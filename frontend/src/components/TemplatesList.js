import React, { useEffect, useMemo, useState } from "react";
import { FiBriefcase, FiFileText, FiHome, FiSearch, FiShield, FiUsers, FiBookOpen } from "react-icons/fi";
import api, { API_BASE_URL } from "../api";

const CATEGORY_ICONS = {
  Business: FiBriefcase,
  Employment: FiUsers,
  Property: FiHome,
  Commercial: FiFileText,
  "Personal & legal": FiShield,
  "Legal proceedings": FiBookOpen,
};

function TemplatesList({ onSelect }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All templates");

  useEffect(() => {
    let cancelled = false;
    api.get(`${API_BASE_URL}/templates`)
      .then((response) => { if (!cancelled) setTemplates(Array.isArray(response.data) ? response.data : []); })
      .catch(() => { if (!cancelled) setError("The template library could not be loaded. Check that the backend is running."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const categories = useMemo(() => [
    "All templates",
    ...Array.from(new Set(templates.map((template) => template.category || "General"))).sort(),
  ], [templates]);

  const filteredTemplates = useMemo(() => {
    const query = search.trim().toLowerCase();
    return templates.filter((template) => {
      const category = template.category || "General";
      const matchesCategory = activeCategory === "All templates" || category === activeCategory;
      const searchable = [template.name, template.description, template.use_case, category, ...(template.parties || [])]
        .filter(Boolean).join(" ").toLowerCase();
      return matchesCategory && (!query || searchable.includes(query));
    });
  }, [templates, search, activeCategory]);

  return (
    <section className="template-library fadein">
      <div className="template-library-header">
        <div>
          <p className="eyebrow mb-2">LEXCHAIN WORKSPACE</p>
          <h1 className="display-6 fw-semibold mb-2">Create a document</h1>
          <p className="text-muted mb-0">Start with a template, enter the details, and review your draft before exporting it.</p>
        </div>
        <div className="template-count">
          <span className="template-count-number">{templates.length}</span>
          <span className="small text-muted">templates</span>
        </div>
      </div>

      <div className="template-tools">
        <div className="template-search-wrap">
          <FiSearch aria-hidden="true" />
          <input
            type="search"
            className="form-control template-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search documents or use cases"
            aria-label="Search document templates"
          />
        </div>
        <div className="template-categories" role="group" aria-label="Filter templates by category">
          {categories.map((category) => (
            <button
              type="button"
              key={category}
              className={`category-chip ${activeCategory === category ? "active" : ""}`}
              onClick={() => setActiveCategory(category)}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {loading && <div className="template-empty"><span className="spinner-border spinner-border-sm me-2" />Loading document templates…</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      {!loading && !error && filteredTemplates.length === 0 && (
        <div className="template-empty">
          <FiSearch size={24} />
          <strong>No matching templates</strong>
          <span className="text-muted">Try another search or choose a different category.</span>
        </div>
      )}

      <div className="template-grid">
        {filteredTemplates.map((template) => {
          const category = template.category || "General";
          const Icon = CATEGORY_ICONS[category] || FiFileText;
          const fieldLabels = (template.fields || []).map((field) => field.label).filter(Boolean);
          return (
            <article className="template-card" key={template.id}>
              <div className="template-card-topline">
                <span className="template-icon"><Icon size={19} aria-hidden="true" /></span>
                <span className="template-category-label">{category}</span>
              </div>
              <h2 className="h5 template-card-title">{template.name}</h2>
              <p className="template-card-description">{template.description}</p>
              {template.use_case && (
                <div className="template-use-case">
                  <span className="small text-muted d-block mb-1">Typical use</span>
                  <span>{template.use_case}</span>
                </div>
              )}
              <div className="template-card-meta">
                <span>{fieldLabels.length} form fields</span>
                {template.parties?.length > 0 && <span>{template.parties.length} parties</span>}
              </div>
              <button type="button" className="btn template-select-button" onClick={() => onSelect(template)}>
                Use this template <span aria-hidden="true">→</span>
              </button>
            </article>
          );
        })}
      </div>

      <div className="template-legal-note">
        <FiShield size={18} aria-hidden="true" />
        <p className="mb-0"><strong>Review before use.</strong> Templates and AI-generated drafts may require jurisdiction-specific review. LexChain does not certify legal validity.</p>
      </div>
    </section>
  );
}

export default TemplatesList;
