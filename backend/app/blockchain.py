"""Lazy blockchain service for LexChain.

The module does not connect to a blockchain during application startup. The service is
created only when a blockchain operation is requested and configuration is available.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)
logger = logging.getLogger(__name__)


class BlockchainConfigurationError(RuntimeError):
    pass


class BlockchainService:
    def __init__(self) -> None:
        try:
            from web3 import Web3
        except ImportError as exc:
            raise BlockchainConfigurationError(
                "Blockchain features require the 'web3' package. Install backend/requirements.txt."
            ) from exc

        self.Web3 = Web3
        self.rpc_url = os.getenv("INFURA_URL", "").strip()
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "").strip()
        self.account_address = os.getenv("ACCOUNT_ADDRESS", "").strip()
        self.private_key = os.getenv("PRIVATE_KEY", "").strip()

        missing = [
            name for name, value in (
                ("INFURA_URL", self.rpc_url),
                ("CONTRACT_ADDRESS", self.contract_address),
                ("ACCOUNT_ADDRESS", self.account_address),
                ("PRIVATE_KEY", self.private_key),
            ) if not value
        ]
        if missing:
            raise BlockchainConfigurationError(
                "Blockchain is not configured. Missing: " + ", ".join(missing)
            )

        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 20}))
        try:
            connected = self.web3.is_connected()
        except Exception as exc:
            raise BlockchainConfigurationError("Could not connect to the configured blockchain RPC.") from exc
        if not connected:
            raise BlockchainConfigurationError("Could not connect to the configured blockchain RPC.")

        if not Web3.is_address(self.contract_address):
            raise BlockchainConfigurationError("CONTRACT_ADDRESS is not a valid Ethereum address.")
        if not Web3.is_address(self.account_address):
            raise BlockchainConfigurationError("ACCOUNT_ADDRESS is not a valid Ethereum address.")

        self.contract_address = Web3.to_checksum_address(self.contract_address)
        self.account_address = Web3.to_checksum_address(self.account_address)
        abi_path = Path(__file__).resolve().parent / "contract_abi.json"
        try:
            with abi_path.open("r", encoding="utf-8") as file:
                abi = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise BlockchainConfigurationError("Could not load the blockchain contract ABI.") from exc

        self.contract = self.web3.eth.contract(address=self.contract_address, abi=abi)
        contract_code = self.web3.eth.get_code(self.contract_address)
        if not contract_code:
            raise BlockchainConfigurationError("CONTRACT_ADDRESS does not contain a deployed contract.")

    def hash_document(self, document: str) -> str:
        return self.web3.keccak(text=document).hex()

    def notarize_hash_on_chain(self, document_hash: str) -> str:
        try:
            hash_bytes = self.web3.to_bytes(hexstr=document_hash)
            if len(hash_bytes) != 32:
                raise ValueError("Document hash must be exactly 32 bytes.")
            nonce = self.web3.eth.get_transaction_count(self.account_address, "pending")
            transaction = self.contract.functions.notarizeDocument(hash_bytes).build_transaction({
                "from": self.account_address,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
                "gas": 300000,
                "gasPrice": self.web3.eth.gas_price,
            })
            signed = self.web3.eth.account.sign_transaction(transaction, private_key=self.private_key)
            raw_transaction = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
            if raw_transaction is None:
                raise RuntimeError("Web3 returned a signed transaction without raw transaction bytes.")
            tx_hash = self.web3.eth.send_raw_transaction(raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if int(receipt.get("status", 0)) != 1:
                raise RuntimeError("The blockchain transaction was mined but failed.")
            return self.web3.to_hex(tx_hash)
        except Exception as exc:
            logger.exception("Blockchain notarization failed")
            raise RuntimeError(f"Blockchain notarization failed: {exc.__class__.__name__}.") from exc

    def verify_transaction(
        self,
        transaction_hash: str,
        expected_document_hash: str,
        expected_sender: str | None = None,
    ) -> dict[str, str | int]:
        """Confirm a successful transaction to this contract and the stored document hash."""
        try:
            transaction = self.web3.eth.get_transaction(transaction_hash)
            receipt = self.web3.eth.get_transaction_receipt(transaction_hash)
            if int(receipt.get("status", 0)) != 1:
                raise ValueError("Transaction did not succeed.")
            if not transaction.get("to") or transaction["to"].lower() != self.contract_address.lower():
                raise ValueError("Transaction was not sent to the configured LexChain contract.")
            tx_sender = self.Web3.to_checksum_address(transaction["from"])
            if expected_sender and tx_sender.lower() != expected_sender.lower():
                raise ValueError("Transaction sender does not match the submitted sender.")

            hash_bytes = self.web3.to_bytes(hexstr=expected_document_hash)
            if len(hash_bytes) != 32:
                raise ValueError("Document hash must be exactly 32 bytes.")
            expected_calldata = self.contract.encode_abi("notarizeDocument", args=[hash_bytes]).lower()
            raw_calldata = transaction.get("input", transaction.get("data", "0x"))
            actual_calldata = (
                "0x" + bytes(raw_calldata).hex()
                if isinstance(raw_calldata, (bytes, bytearray))
                else str(raw_calldata).lower()
            )
            if actual_calldata != expected_calldata:
                raise ValueError("Transaction does not call notarizeDocument with the expected document hash.")
            recorded_sender, recorded_timestamp = self.contract.functions.verifyDocument(hash_bytes).call()
            timestamp = int(recorded_timestamp)
            if timestamp <= 0:
                raise ValueError("The expected document hash is not recorded by the contract.")
            if self.Web3.to_checksum_address(recorded_sender).lower() != tx_sender.lower():
                raise ValueError("The recorded notarizer does not match the transaction sender.")
            return {
                "sender": self.Web3.to_checksum_address(recorded_sender),
                "timestamp": timestamp,
                "transaction_hash": self.web3.to_hex(receipt["transactionHash"]),
            }
        except Exception as exc:
            logger.warning("Blockchain transaction verification failed: %s", exc.__class__.__name__)
            raise ValueError(f"Blockchain transaction could not be verified: {exc}") from exc


@lru_cache(maxsize=1)
def get_blockchain_service() -> BlockchainService:
    """Create and cache the blockchain service on first use, never at app startup."""
    return BlockchainService()
