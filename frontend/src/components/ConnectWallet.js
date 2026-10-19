import React, { useEffect, useState } from "react";
import { ethers } from "ethers";
import { OverlayTrigger, Tooltip, Button, Spinner } from "react-bootstrap";

/**
 * ConnectWallet - Enhanced MetaMask wallet connect button with:
 * - Copyable address (shows full on tooltip)
 * - ETH balance display
 * - Network info & error if not Sepolia
 * - Disconnect feature
 *
 * Usage:
 * <ConnectWallet wallet={wallet} setWallet={setWallet} />
 */
function ConnectWallet({ wallet, setWallet }) {
  const [connecting, setConnecting] = useState(false);
  const [balance, setBalance] = useState(null);
  const [copied, setCopied] = useState(false);
  const [network, setNetwork] = useState(null);
  const [error, setError] = useState("");

  // Helper to truncate address
  const shortAddress = (addr) => addr ? `${addr.slice(0, 6)}...${addr.slice(-4)}` : "";

  // Fetch ETH balance and network
  useEffect(() => {
    async function fetchBalanceAndNetwork() {
      if (wallet && window.ethereum) {
        try {
          const provider = new ethers.BrowserProvider(window.ethereum);
          const balanceWei = await provider.getBalance(wallet);
          setBalance(ethers.formatEther(balanceWei));
          const net = await provider.getNetwork();
          setNetwork(net);
        } catch (err) {
          setBalance(null);
          setNetwork(null);
        }
      }
    }
    fetchBalanceAndNetwork();
  }, [wallet]);

  // Listen for account or network change
  useEffect(() => {
    if (window.ethereum) {
      const handleAccountsChanged = (accounts) => {
        setWallet(accounts[0] || null);
      };
      const handleChainChanged = () => {
        window.location.reload();
      };
      window.ethereum.on("accountsChanged", handleAccountsChanged);
      window.ethereum.on("chainChanged", handleChainChanged);
      return () => {
        window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
        window.ethereum.removeListener("chainChanged", handleChainChanged);
      };
    }
  }, [setWallet]);

  // Copy wallet address
  const handleCopy = () => {
    if (wallet) {
      navigator.clipboard.writeText(wallet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }
  };

  // Connect wallet
  const handleConnect = async () => {
    setConnecting(true);
    setError("");
    try {
      if (!window.ethereum) {
        setError("MetaMask is not installed.");
        setConnecting(false);
        return;
      }
      const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
      setWallet(accounts[0]);
    } catch (err) {
      setError("Failed to connect wallet.");
    }
    setConnecting(false);
  };

  const wrongNetwork = network && network.chainId !== 11155111; // Sepolia (change if needed)
  const networkName = network ? (network.name === "unknown" ? `ChainId ${network.chainId}` : network.name) : "";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
      {!wallet ? (
        <>
          <Button
            variant="outline-primary"
            onClick={handleConnect}
            disabled={connecting}
            style={{ fontWeight: 600, borderRadius: 20, padding: "6px 18px" }}
          >
            {connecting ? <Spinner animation="border" size="sm" className="me-2" /> : null}
            Connect MetaMask
          </Button>
          {error && <span className="text-danger ms-2">{error}</span>}
        </>
      ) : (
        <div className="d-flex align-items-center gap-2">
          <OverlayTrigger
            placement="bottom"
            overlay={<Tooltip id="address-tooltip">{wallet}</Tooltip>}
          >
            <Button
              variant="outline-dark"
              style={{
                fontWeight: 600,
                borderRadius: 20,
                padding: "6px 14px",
                background: "#fff",
                border: "1px solid #bdbdbd",
                position: "relative",
              }}
              onClick={handleCopy}
              title="Copy Address"
            >
              <i className="bi bi-wallet2 me-1" />
              {shortAddress(wallet)}
              <i
                className={`bi ms-2 ${copied ? "bi-clipboard-check-fill text-success" : "bi-clipboard"} `}
                style={{ fontSize: 17, verticalAlign: "-2px" }}
              />
            </Button>
          </OverlayTrigger>
          {balance !== null && (
            <span
              style={{
                fontFamily: "monospace",
                fontSize: 15,
                background: "#f4f4f6",
                borderRadius: 7,
                padding: "3px 10px",
                border: "1px solid #e0e0e0",
                marginLeft: 6,
              }}
              title="Available ETH Balance"
            >
              <i className="bi bi-currency-ethereum me-1" />
              {Number(balance).toFixed(4)} ETH
            </span>
          )}
          {network && (
            <span
              style={{
                fontFamily: "monospace",
                fontSize: 13,
                background: wrongNetwork ? "#ffeaea" : "#f6f6fa",
                borderRadius: 7,
                padding: "3px 10px",
                border: `1px solid ${wrongNetwork ? "#ff7b7b" : "#e0e0e0"}`,
                color: wrongNetwork ? "#c41c1c" : "#333",
                marginLeft: 4,
              }}
              title={wrongNetwork ? "Switch to Sepolia for notarization" : "Connected Network"}
            >
              <i className="bi bi-globe2 me-1" />
              {networkName}
              {wrongNetwork && (
                <span className="ms-2">
                  <i className="bi bi-exclamation-triangle text-danger" /> Wrong Network
                </span>
              )}
            </span>
          )}
          <Button
            variant="outline-danger"
            size="sm"
            onClick={() => setWallet(null)}
            style={{ borderRadius: 18, fontSize: 15, marginLeft: 8 }}
            title="Disconnect"
          >
            <i className="bi bi-box-arrow-right" />
          </Button>
        </div>
      )}
    </div>
  );
}

export default ConnectWallet;
