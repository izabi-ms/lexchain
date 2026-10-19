import React, { useState } from "react";
import api, { API_BASE_URL } from "../api";

function VerificationPage() {
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState("");
  const [result, setResult] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const handleVerify = async () => {
    if (!file || !docId || !/^\d+$/.test(docId)) {
      setResult({ valid: false, reason: "Select a PDF and enter a valid document reference." });
      return;
    }

    setVerifying(true);
    setResult(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await api.post(
        `${API_BASE_URL}/verify_pdf/${docId}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(response.data);
    } catch (error) {
      setResult({
        valid: false,
        reason: typeof error?.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Verification could not be completed. Check the document reference and try again.",
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <section className="card silky-card shadow-sm fadein">
      <div className="card-body p-4 p-md-5">
        <p className="text-uppercase small fw-semibold text-primary mb-2">Document integrity</p>
        <h2 className="h4 mb-2">Verify a LexChain document</h2>
        <p className="text-muted mb-4">
          Upload a PDF and provide its document reference to check for the LexChain reference marker.
        </p>
        <div className="mb-3">
          <label className="form-label" htmlFor="document-reference">Document reference</label>
          <input
            id="document-reference"
            type="number"
            min="1"
            className="form-control"
            value={docId}
            onChange={(event) => setDocId(event.target.value)}
            placeholder="Enter document ID"
          />
        </div>
        <div className="mb-4">
          <label className="form-label" htmlFor="document-pdf">PDF file</label>
          <input
            id="document-pdf"
            type="file"
            accept="application/pdf,.pdf"
            className="form-control"
            onChange={(event) => { setFile(event.target.files?.[0] || null); setResult(null); }}
          />
        </div>
        <button className="btn silky-btn silky-btn-primary" disabled={verifying} onClick={handleVerify}>
          {verifying ? "Checking document…" : "Verify document"}
        </button>
        {result && (
          <div className={`alert mt-4 mb-0 ${result.valid ? "alert-success" : "alert-warning"}`} role="status">
            <strong>{result.valid ? "Reference marker matched" : "Could not verify the marker"}</strong>
            <p className="mb-1 mt-2">{result.reason || "No additional details were returned."}</p>
            {result.verification_level === "metadata_marker_only" && (
              <small>This check currently validates PDF metadata only, not the full document contents.</small>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default VerificationPage;
