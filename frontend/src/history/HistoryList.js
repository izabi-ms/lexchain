import React, { useEffect, useState } from "react";
import api, { API_BASE_URL } from "../api";
import { FiDownload, FiEye, FiFileText, FiShield, FiTrash2 } from "react-icons/fi";

function HistoryList({ wallet, setDocument, setDocId, setStatus, setPage, setSelectedTemplate }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function fetchHistory() {
      if (!wallet) {
        setHistory([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError("");
      try {
        const response = await api.get(`${API_BASE_URL}/history`, { params: { sender: wallet } });
        if (!cancelled) setHistory(Array.isArray(response.data) ? response.data : []);
      } catch {
        if (!cancelled) setError("Your document history could not be loaded. Please try again.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchHistory();
    return () => { cancelled = true; };
  }, [wallet, success]);

  const openDocument = (item) => {
    setSelectedTemplate(null);
    setDocument(item.generated_text);
    setDocId(item.document_id);
    setStatus(item.transaction_hash ? {
      txHash: item.transaction_hash,
      docHash: item.document_hash,
      sender: item.sender,
    } : null);
    setPage("generate");
  };

  const handleDelete = async (item) => {
    const confirmed = window.confirm(`Delete document #${item.document_id}? This cannot be undone.`);
    if (!confirmed) return;
    setDeletingId(item.document_id);
    setError("");
    setSuccess("");
    try {
      await api.delete(`${API_BASE_URL}/document/${item.document_id}`);
      setHistory((current) => current.filter((document) => document.document_id !== item.document_id));
      setSuccess(`Document #${item.document_id} was deleted.`);
    } catch (deleteError) {
      setError(deleteError?.response?.data?.detail || "The document could not be deleted. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownloadPdf = async (item) => {
    setError("");
    try {
      const response = await api.get(`${API_BASE_URL}/pdf/${item.document_id}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `LexChain_Document_${item.document_id}.pdf`;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("The PDF could not be downloaded. It may not have been exported yet.");
    }
  };

  return (
    <section className="history-page fadein">
      <div className="template-library-header">
        <div>
          <p className="eyebrow mb-2">YOUR WORKSPACE</p>
          <h1 className="display-6 fw-semibold mb-2">Document history</h1>
          <p className="text-muted mb-0">Reopen saved drafts and review documents associated with your connected wallet.</p>
        </div>
        <div className="template-count">
          <span className="template-count-number">{history.length}</span>
          <span className="small text-muted">documents</span>
        </div>
      </div>

      {success && <div className="alert alert-success" role="status">{success}</div>}
      {error && <div className="alert alert-warning" role="alert">{error}</div>}
      {!wallet && (
        <div className="history-empty">
          <FiShield size={28} />
          <h2 className="h5">Connect your wallet</h2>
          <p className="text-muted mb-0">Connect the wallet used to record document hashes to view its associated history.</p>
        </div>
      )}
      {wallet && loading && <div className="history-empty"><span className="spinner-border spinner-border-sm me-2" />Loading your documents…</div>}
      {wallet && !loading && history.length === 0 && !error && (
        <div className="history-empty">
          <FiFileText size={28} />
          <h2 className="h5">No documents yet</h2>
          <p className="text-muted mb-3">Documents recorded by this wallet will appear here.</p>
          <button className="btn silky-btn silky-btn-primary" onClick={() => setPage("generate")}>Create a document</button>
        </div>
      )}

      {wallet && !loading && history.length > 0 && (
        <div className="history-list">
          {history.map((item) => (
            <article className="history-row" key={item.document_id}>
              <div className="history-file-icon"><FiFileText size={21} aria-hidden="true" /></div>
              <div className="history-row-content">
                <div className="d-flex align-items-center flex-wrap gap-2 mb-1">
                  <h2 className="h6 mb-0">{item.document_type || "Untitled document"}</h2>
                  <span className="history-reference">#{item.document_id}</span>
                  {item.transaction_hash ? <span className="status-pill status-pill-success">Hash recorded</span> : <span className="status-pill">Draft</span>}
                </div>
                <p className="history-excerpt mb-2">{(item.generated_text || "").slice(0, 150)}{(item.generated_text || "").length > 150 ? "…" : ""}</p>
                <div className="history-metadata">
                  <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Date unavailable"}</span>
                  {item.sender && <span>Wallet {`${item.sender.slice(0, 6)}…${item.sender.slice(-4)}`}</span>}
                </div>
              </div>
              <div className="history-row-actions">
                <button type="button" className="icon-action" onClick={() => openDocument(item)} aria-label={`Open document ${item.document_id}`} title="Open document"><FiEye /></button>
                {item.has_pdf && <button type="button" className="icon-action" onClick={() => handleDownloadPdf(item)} aria-label={`Download PDF ${item.document_id}`} title="Download PDF"><FiDownload /></button>}
                <button type="button" className="icon-action icon-action-danger" onClick={() => handleDelete(item)} disabled={deletingId === item.document_id} aria-label={`Delete document ${item.document_id}`} title="Delete document">
                  {deletingId === item.document_id ? <span className="spinner-border spinner-border-sm" /> : <FiTrash2 />}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default HistoryList;
