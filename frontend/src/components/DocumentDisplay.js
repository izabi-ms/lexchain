import React, { useEffect, useMemo, useState } from "react";
import { ethers } from "ethers";
import api, { API_BASE_URL } from "../api";
import { jsPDF } from "jspdf";
import contractABI from "../abi/contract_abi.json";

const API_URL = API_BASE_URL;

function DocumentDisplay({ document, docId, setStatus, wallet, status, setDocument, setDocId }) {
  const [historyDocs, setHistoryDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [notarizing, setNotarizing] = useState(false);
  const [notarizeError, setNotarizeError] = useState("");
  const [notarizeSuccess, setNotarizeSuccess] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [watermarking, setWatermarking] = useState(false);
  const [watermarkError, setWatermarkError] = useState("");
  const [pdfStatus, setPdfStatus] = useState("");

  const selectedDoc = useMemo(
    () => historyDocs.find((item) => String(item.document_id) === String(selectedDocId)),
    [historyDocs, selectedDocId]
  );
  const activeDocumentId = selectedDoc ? selectedDoc.document_id : docId;
  const displayText = isEditing ? editedText : (selectedDoc?.generated_text || document || "");

  useEffect(() => {
    let cancelled = false;
    async function fetchHistory() {
      if (!wallet) {
        setHistoryDocs([]);
        return;
      }
      try {
        const response = await api.get(`${API_URL}/history`, { params: { sender: wallet } });
        if (!cancelled) setHistoryDocs(Array.isArray(response.data) ? response.data : []);
      } catch {
        if (!cancelled) setHistoryDocs([]);
      }
    }
    fetchHistory();
    return () => { cancelled = true; };
  }, [wallet, docId, status?.txHash]);

  useEffect(() => {
    if (selectedDoc) {
      setEditedText(selectedDoc.generated_text);
      setIsEditing(false);
      setStatus(selectedDoc.transaction_hash ? {
        txHash: selectedDoc.transaction_hash,
        docHash: selectedDoc.document_hash,
        sender: selectedDoc.sender,
      } : null);
      setPdfStatus("");
      setNotarizeSuccess(false);
    }
  }, [selectedDoc, setStatus]);

  useEffect(() => {
    if (!selectedDoc && document) setEditedText(document);
  }, [document, selectedDoc]);

  const handleSelectDocument = (event) => {
    const value = event.target.value;
    setSelectedDocId(value);
    setSaveError("");
    setSaveSuccess(false);
    setNotarizeError("");
    setWatermarkError("");
    if (!value) {
      setStatus(null);
      setIsEditing(Boolean(document));
      setEditedText(document || "");
    }
  };

  const handleSaveEdited = async () => {
    setSaveError("");
    setSaveSuccess(false);
    if (!editedText.trim()) {
      setSaveError("The document cannot be empty.");
      return;
    }
    setSaving(true);
    try {
      const response = await api.post(`${API_URL}/document`, {
        client_data: "Edited document",
        document_type: selectedDoc?.document_type || "Custom document",
        generated_text: editedText.trim(),
      });
      const newId = response.data.document_id;
      setDocId(newId);
      setDocument(editedText.trim());
      setSelectedDocId("");
      setStatus(null);
      setIsEditing(false);
      setSaveSuccess(true);
    } catch (error) {
      setSaveError(error?.response?.data?.detail || "Saving failed. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleNotarize = async () => {
    setNotarizing(true);
    setNotarizeError("");
    setNotarizeSuccess(false);
    try {
      if (!window.ethereum || !wallet) throw new Error("Connect MetaMask before notarizing.");
      if (!activeDocumentId) throw new Error("Save the document before notarizing it.");
      if (!displayText.trim()) throw new Error("There is no document text to notarize.");

      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = await provider.getSigner();
      let network = await provider.getNetwork();
      if (network.chainId !== 11155111n) {
        await window.ethereum.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: "0xaa36a7" }],
        });
        network = await provider.getNetwork();
        if (network.chainId !== 11155111n) throw new Error("Please switch MetaMask to the Sepolia network.");
      }

      const contractAddress = process.env.REACT_APP_CONTRACT_ADDRESS;
      if (!contractAddress) throw new Error("The LexChain contract address is not configured.");
      const contract = new ethers.Contract(contractAddress, contractABI, signer);
      const documentHash = ethers.keccak256(ethers.toUtf8Bytes(displayText));
      const transaction = await contract.notarizeDocument(documentHash);
      const receipt = await transaction.wait();
      if (!receipt || receipt.status !== 1) throw new Error("The blockchain transaction did not succeed.");

      const nextStatus = { txHash: transaction.hash, docHash: documentHash, sender: wallet };
      await api.post(`${API_URL}/saveTx`, {
        document_id: activeDocumentId,
        transaction_hash: transaction.hash,
        document_hash: documentHash,
        sender: wallet,
      });
      setStatus(nextStatus);
      setNotarizeSuccess(true);
      setPdfStatus("Transaction confirmed. The backend has verified the transaction before recording it.");
    } catch (error) {
      setNotarizeError(error?.response?.data?.detail || error?.shortMessage || error?.message || "Notarization failed.");
    } finally {
      setNotarizing(false);
    }
  };

  const handleAddReferenceMarker = async () => {
    if (!activeDocumentId) return;
    setWatermarking(true);
    setWatermarkError("");
    try {
      await api.post(`${API_URL}/watermark_pdf/${activeDocumentId}`);
      setPdfStatus("LexChain document reference metadata was added. This marker is not a substitute for full content-integrity verification.");
    } catch (error) {
      setWatermarkError(error?.response?.data?.detail || "Could not add the document reference marker.");
    } finally {
      setWatermarking(false);
    }
  };

  const handleDownloadPDF = async () => {
    const textToExport = (displayText || "").trim();
    if (!textToExport) {
      setSaveError("Generate or select a document before exporting it.");
      return;
    }

    const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 20;
    const textWidth = pageWidth - margin * 2;
    let y = 22;

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(18);
    pdf.setTextColor(23, 43, 77);
    pdf.text("LEXCHAIN", margin, y);
    y += 7;
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(9);
    pdf.setTextColor(91, 101, 115);
    pdf.text("AI-assisted document draft", margin, y);
    y += 8;
    pdf.setDrawColor(220, 225, 232);
    pdf.line(margin, y, pageWidth - margin, y);
    y += 9;

    pdf.setFontSize(9);
    pdf.setTextColor(80, 88, 100);
    pdf.text(`Document reference: ${activeDocumentId || "Draft"}`, margin, y);
    y += 5;
    pdf.text(`Exported: ${new Date().toLocaleDateString()}`, margin, y);
    y += 10;

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(11);
    pdf.setTextColor(32, 41, 56);
    const paragraphs = textToExport.split(/\n\s*\n/);
    for (const paragraph of paragraphs) {
      const lines = pdf.splitTextToSize(paragraph.trim(), textWidth);
      for (const line of lines) {
        if (y > pageHeight - margin - 24) {
          pdf.addPage();
          y = margin;
        }
        pdf.text(line, margin, y);
        y += 5.5;
      }
      y += 3;
    }

    const disclaimer = "Important: This document was generated with AI assistance and requires human review. It is not a substitute for advice from a qualified legal professional.";
    const disclaimerLines = pdf.splitTextToSize(disclaimer, textWidth);
    if (y + disclaimerLines.length * 4.5 > pageHeight - margin) {
      pdf.addPage();
      y = margin;
    }
    y += 4;
    pdf.setFontSize(8);
    pdf.setTextColor(91, 101, 115);
    pdf.text(disclaimerLines, margin, y);

    if (status?.txHash && status?.docHash) {
      pdf.addPage();
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(11);
      pdf.setTextColor(23, 43, 77);
      pdf.text("Blockchain record", margin, margin);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(8);
      pdf.setTextColor(45, 55, 72);
      const txLines = pdf.splitTextToSize(`Transaction: ${status.txHash}`, textWidth);
      pdf.text(txLines, margin, margin + 9);
      const hashLines = pdf.splitTextToSize(`Document text hash: ${status.docHash}`, textWidth);
      pdf.text(hashLines, margin, margin + 23);
      pdf.text(`Recorded sender: ${status.sender || "Not available"}`, margin, margin + 37);
      pdf.text("A blockchain record does not by itself establish legal validity or truth of contents.", margin, margin + 47);
    }

    const exportId = activeDocumentId || "draft";
    const blob = pdf.output("blob");
    pdf.save(`LexChain_Document_${exportId}.pdf`);

    if (activeDocumentId) {
      const formData = new FormData();
      formData.append("pdf", blob, `LexChain_Document_${activeDocumentId}.pdf`);
      try {
        const response = await api.post(
          `${API_URL}/savePdf?document_id=${activeDocumentId}`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );
        if (response.data?.ipfs_backup === "stored_encrypted") {
          setPdfStatus("PDF saved. An encrypted backup was also pinned to IPFS.");
        } else {
          setPdfStatus("PDF downloaded. A local copy was saved by LexChain; encrypted IPFS backup is not configured.");
        }
      } catch (error) {
        setPdfStatus("PDF downloaded, but LexChain could not save a server copy.");
      }
    }
  };

  return (
    <section className="card mt-4 silky-card shadow-sm fadein">
      <div className="card-body p-4 p-md-5">
        <div className="d-flex align-items-start justify-content-between flex-wrap gap-3 mb-4">
          <div>
            <p className="text-uppercase small fw-semibold text-primary mb-2">Document workspace</p>
            <h2 className="h4 mb-1">Review your document</h2>
            <p className="text-muted small mb-0">Review the draft before saving, exporting or recording its hash.</p>
          </div>
          <span className={`badge rounded-pill ${status?.txHash ? "text-bg-success" : "text-bg-secondary"}`}>
            {status?.txHash ? "Blockchain record confirmed" : "Draft / not recorded"}
          </span>
        </div>

        {wallet && historyDocs.length > 0 && (
          <div className="mb-3">
            <label className="form-label" htmlFor="previous-document">Open a previous document</label>
            <select id="previous-document" className="form-select" value={selectedDocId} onChange={handleSelectDocument}>
              <option value="">Current document</option>
              {historyDocs.map((item) => (
                <option key={item.document_id} value={String(item.document_id)}>
                  {(item.document_type || "Untitled") + ` · #${item.document_id}`}
                </option>
              ))}
            </select>
          </div>
        )}

        {isEditing ? (
          <textarea
            className="form-control document-editor"
            value={editedText}
            onChange={(event) => setEditedText(event.target.value)}
            placeholder="Your generated document will appear here…"
            aria-label="Edit document text"
          />
        ) : (
          <div className="document-preview" aria-label="Document preview">
            {displayText || <span className="text-muted">Generate a document from the template library to see it here.</span>}
          </div>
        )}

        {isEditing && (
          <div className="d-flex gap-2 mt-3 flex-wrap">
            <button className="btn silky-btn silky-btn-primary" onClick={handleSaveEdited} disabled={saving || !editedText.trim()}>
              {saving ? "Saving…" : "Save as new version"}
            </button>
            <button className="btn btn-outline-secondary" onClick={() => setIsEditing(false)} disabled={saving}>
              Cancel editing
            </button>
          </div>
        )}

        <div className="d-flex gap-2 mt-4 flex-wrap">
          <button
            className="btn silky-btn silky-btn-primary"
            onClick={handleNotarize}
            disabled={notarizing || !wallet || !activeDocumentId || !displayText.trim() || Boolean(status?.txHash) || isEditing}
            title={!wallet ? "Connect MetaMask first" : !activeDocumentId ? "Save the document first" : status?.txHash ? "This document already has a recorded hash" : ""}
          >
            {notarizing ? "Confirming transaction…" : status?.txHash ? "Hash recorded" : "Record hash on blockchain"}
          </button>
          <button
            className="btn btn-outline-primary"
            onClick={handleAddReferenceMarker}
            disabled={watermarking || !activeDocumentId || !status?.txHash}
          >
            {watermarking ? "Adding marker…" : "Add document reference marker"}
          </button>
          <button className="btn btn-outline-secondary" onClick={handleDownloadPDF} disabled={!displayText.trim()}>
            Download PDF
          </button>
          {!isEditing && displayText && (
            <button className="btn btn-outline-secondary" onClick={() => { setEditedText(displayText); setIsEditing(true); }}>
              Edit document
            </button>
          )}
        </div>

        {saveError && <div className="alert alert-danger mt-3 mb-0">{saveError}</div>}
        {saveSuccess && <div className="alert alert-success mt-3 mb-0">A new editable document version was saved.</div>}
        {notarizeError && <div className="alert alert-danger mt-3 mb-0">{notarizeError}</div>}
        {watermarkError && <div className="alert alert-danger mt-3 mb-0">{watermarkError}</div>}
        {pdfStatus && <div className="alert alert-info mt-3 mb-0">{pdfStatus}</div>}
        {notarizeSuccess && status?.txHash && (
          <div className="alert alert-success mt-3 mb-0">
            Transaction confirmed. <a href={`https://sepolia.etherscan.io/tx/${status.txHash}`} target="_blank" rel="noreferrer">View transaction</a>
          </div>
        )}
        {status?.txHash && (
          <div className="border rounded-3 p-3 mt-3">
            <div className="fw-semibold mb-2">Blockchain record</div>
            <div className="small text-muted">Transaction hash</div>
            <code className="d-block text-break mb-2">{status.txHash}</code>
            <div className="small text-muted">Document text hash</div>
            <code className="d-block text-break mb-2">{status.docHash}</code>
            <div className="small text-muted">Sender</div>
            <code className="d-block text-break">{status.sender || "Not available"}</code>
          </div>
        )}
        {!wallet && <p className="text-muted small mt-3 mb-0">Connect MetaMask if you want to record a document hash on the Sepolia test network.</p>}
      </div>
    </section>
  );
}

export default DocumentDisplay;
