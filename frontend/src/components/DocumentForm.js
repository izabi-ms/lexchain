import React, { useMemo, useState } from "react";
import api, { API_BASE_URL } from "../api";
import { FiArrowLeft, FiCalendar, FiFileText, FiShield } from "react-icons/fi";

function getFieldType(field) {
  const text = `${field.label || ""} ${field.id || ""}`.toLowerCase();
  if (text.includes("date") || text.includes("start") || text.includes("end")) return "date";
  if (text.includes("email")) return "email";
  if (text.includes("phone")) return "tel";
  if (text.includes("website") || text.includes("url")) return "url";
  return "text";
}

function isLongField(field) {
  const text = `${field.label || ""} ${field.id || ""}`.toLowerCase();
  return ["description", "purpose", "address", "scope", "responsibilities", "terms", "details", "obligations"]
    .some((word) => text.includes(word));
}

function DocumentForm({ template, setDocument, setDocId, setStatus, onBack }) {
  const initialFields = useMemo(
    () => Object.fromEntries((template.fields || []).map((field) => [field.id, ""])),
    [template]
  );
  const [fields, setFields] = useState(initialFields);
  const [docDate, setDocDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [streamedText, setStreamedText] = useState("");
  const [finished, setFinished] = useState(false);

  const handleChange = (fieldId, value) => {
    setFields((current) => ({ ...current, [fieldId]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    setFinished(false);
    setStreamedText("");

    let generatedText = "";
    try {
      const requestFields = { ...fields };
      if (docDate) {
        const dateField = template.fields.find((field) => /document date/i.test(field.label || ""));
        if (dateField) requestFields[dateField.id] = docDate;
      }

      const response = await fetch(`${API_BASE_URL}/generate/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: template.id, fields: requestFields }),
      });

      if (!response.ok) {
        let message = "Document generation failed. Check your inputs and try again.";
        try {
          const payload = await response.json();
          if (typeof payload.detail === "string") message = payload.detail;
          else if (payload.detail?.message) message = payload.detail.message;
          else if (Array.isArray(payload.detail?.missing_fields)) message = `Complete these fields: ${payload.detail.missing_fields.join(", ")}`;
        } catch { /* Keep the fallback for non-JSON errors. */ }
        setError(message);
        return;
      }
      if (!response.body) throw new Error("The server did not return a document stream.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        generatedText += decoder.decode(value, { stream: true });
        setStreamedText(generatedText);
      }
      generatedText += decoder.decode();
      setStreamedText(generatedText);
      if (!generatedText.trim()) throw new Error("The AI provider returned an empty draft. Please try again.");

      // Start a new document record only after generation succeeds; a failed attempt must not orphan the current document.
      setDocId(null);
      setStatus(null);
      setDocument(generatedText);
      setFinished(true);
      try {
        const saveResponse = await api.post(`${API_BASE_URL}/document`, {
          client_data: Object.values(requestFields).join(", ") || "Document form submission",
          document_type: template.name,
          generated_text: generatedText,
          date: docDate || new Date().toISOString().slice(0, 10),
        });
        setDocId(saveResponse.data.document_id);
      } catch {
        setError("Your draft was generated but could not be saved to history. Copy or download it before leaving this page.");
      }
    } catch (generationError) {
      if (generatedText.trim()) setDocument(generatedText);
      setError(generationError?.message || "Generation was interrupted. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="document-form-card fadein">
      <div className="document-form-heading">
        <button type="button" className="back-link" onClick={onBack} disabled={loading}>
          <FiArrowLeft aria-hidden="true" /> Template library
        </button>
        <div className="d-flex align-items-start gap-3 mt-3">
          <div className="template-icon template-icon-large"><FiFileText size={22} aria-hidden="true" /></div>
          <div>
            <span className="template-category-label">{template.category || "Document template"}</span>
            <h1 className="h3 mt-2 mb-2">{template.name}</h1>
            <p className="text-muted mb-0">{template.description}</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="document-form-body" autoComplete="off">
        <div className="form-section-heading">
          <div>
            <h2 className="h6 mb-1">Document details</h2>
            <p className="text-muted small mb-0">Complete the fields below. Required fields are marked with an asterisk.</p>
          </div>
          <span className="field-count">{template.fields.length} fields</span>
        </div>

        <div className="row g-3">
          <div className="col-12 col-md-6">
            <label className="form-label" htmlFor="lexchain-document-date">
              <FiCalendar className="me-2" aria-hidden="true" />Document date <span className="text-muted fw-normal">(optional)</span>
            </label>
            <input
              id="lexchain-document-date"
              type="date"
              className="form-control"
              value={docDate}
              onChange={(event) => setDocDate(event.target.value)}
              disabled={loading}
            />
          </div>
          {template.fields.map((field) => {
            const inputType = getFieldType(field);
            const longField = isLongField(field);
            return (
              <div className={longField ? "col-12" : "col-12 col-md-6"} key={field.id}>
                <label className="form-label" htmlFor={`field-${field.id}`}>
                  {field.label || field.id}{field.required === false ? <span className="text-muted fw-normal"> (optional)</span> : <span className="text-danger ms-1">*</span>}
                </label>
                {longField ? (
                  <textarea
                    id={`field-${field.id}`}
                    className="form-control"
                    rows={3}
                    value={fields[field.id] || ""}
                    onChange={(event) => handleChange(field.id, event.target.value)}
                    required={field.required !== false}
                    placeholder={`Enter ${String(field.label || field.id).toLowerCase()}`}
                    disabled={loading}
                  />
                ) : (
                  <input
                    id={`field-${field.id}`}
                    type={inputType}
                    className="form-control"
                    value={fields[field.id] || ""}
                    onChange={(event) => handleChange(field.id, event.target.value)}
                    required={field.required !== false}
                    placeholder={`Enter ${String(field.label || field.id).toLowerCase()}`}
                    disabled={loading}
                  />
                )}
              </div>
            );
          })}
        </div>

        <div className="form-submit-row">
          <div className="form-safety-note">
            <FiShield size={17} aria-hidden="true" />
            <span>Review the generated draft carefully before signing or relying on it.</span>
          </div>
          <div className="d-flex gap-2 flex-wrap">
            {onBack && <button type="button" className="btn btn-outline-secondary" onClick={onBack} disabled={loading}>Cancel</button>}
            <button type="submit" className="btn silky-btn silky-btn-primary" disabled={loading}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" role="status" />Generating draft…</> : finished ? "Generate again" : "Generate document"}
            </button>
          </div>
        </div>

        {error && <div className="alert alert-warning mt-3 mb-0" role="alert">{error}</div>}
        {loading && (
          <div className="generation-preview mt-4" aria-live="polite">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <strong>Draft in progress</strong><span className="small text-muted">Streaming from NVIDIA NIM</span>
            </div>
            <pre>{streamedText || "Preparing your document…"}</pre>
          </div>
        )}
      </form>
    </section>
  );
}

export default DocumentForm;
