import React from "react";

function BlockchainStatus({ status }) {
  return (
    <div className="alert alert-info mt-4">
      <strong>Blockchain Status:</strong>
      <div>Transaction Hash: <code>{status.txHash}</code></div>
      <div>Document Hash: <code>{status.docHash}</code></div>
      <div>Sender: <code>{status.sender}</code></div>
      <div>
        <a
          href={`https://sepolia.etherscan.io/tx/${status.txHash}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          View on Etherscan
        </a>
      </div>
    </div>
  );
}

export default BlockchainStatus;
