import React, { useState } from "react";
import { Container, Navbar, Nav, ToastContainer } from "react-bootstrap";
import { FiFileText, FiFolder, FiShield } from "react-icons/fi";
import DocumentForm from "./components/DocumentForm";
import DocumentDisplay from "./components/DocumentDisplay";
import ConnectWallet from "./components/ConnectWallet";
import HistoryList from "./history/HistoryList";
import SettingsModal from "./components/SettingsModal";
import TemplatesList from "./components/TemplatesList";
import VerificationPage from "./components/VerificationPage";

function App() {
  const [document, setDocument] = useState(null);
  const [docId, setDocId] = useState(null);
  const [status, setStatus] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [theme, setTheme] = useState("light");
  const [showSettings, setShowSettings] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [page, setPage] = useState("generate");
  const [navExpanded, setNavExpanded] = useState(false);

  const navigate = (nextPage) => {
    if (nextPage === "generate") setSelectedTemplate(null);
    setPage(nextPage);
    setNavExpanded(false);
  };

  return (
    <div className="lexchain-app" data-theme={theme}>
      <Navbar expand="lg" expanded={navExpanded} onToggle={setNavExpanded} className="silky-navbar" variant={theme === "dark" ? "dark" : "light"}>
        <Container fluid="xl">
          <Navbar.Brand className="lexchain-brand" onClick={() => navigate("generate")} role="button" tabIndex={0}>
            <span className="brand-mark"><FiFileText size={21} aria-hidden="true" /></span>
            <span className="brand-copy"><strong>LexChain</strong><small>Business documents, clearly managed</small></span>
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="lexchain-navigation" aria-label="Toggle navigation" />
          <Navbar.Collapse id="lexchain-navigation">
            <Nav className="mx-lg-auto lexchain-nav">
              <Nav.Link active={page === "generate"} onClick={() => navigate("generate")}>
                <FiFileText aria-hidden="true" /> Create document
              </Nav.Link>
              <Nav.Link active={page === "history"} onClick={() => navigate("history")}>
                <FiFolder aria-hidden="true" /> History
              </Nav.Link>
              <Nav.Link active={page === "verify-lexchain"} onClick={() => navigate("verify-lexchain")}>
                <FiShield aria-hidden="true" /> Verify
              </Nav.Link>
            </Nav>
            <div className="navbar-actions">
              <button type="button" className="settings-button" onClick={() => setShowSettings(true)}>Settings</button>
              <ConnectWallet wallet={wallet} setWallet={setWallet} />
            </div>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <main className="lexchain-main">
        <Container fluid="xl">
          {showSettings && (
            <SettingsModal
              show={showSettings}
              onHide={() => setShowSettings(false)}
              theme={theme}
              setTheme={setTheme}
            />
          )}

          {page === "history" && (
            <HistoryList
              wallet={wallet}
              setDocument={setDocument}
              setDocId={setDocId}
              setStatus={setStatus}
              setPage={setPage}
              setSelectedTemplate={setSelectedTemplate}
            />
          )}

          {page === "generate" && (
            <>
              {selectedTemplate ? (
                <DocumentForm
                  template={selectedTemplate}
                  setDocument={setDocument}
                  setDocId={setDocId}
                  setStatus={setStatus}
                  onBack={() => setSelectedTemplate(null)}
                />
              ) : (
                <TemplatesList onSelect={setSelectedTemplate} />
              )}
              {(document || docId) && (
                <DocumentDisplay
                  document={document}
                  docId={docId}
                  setStatus={setStatus}
                  wallet={wallet}
                  status={status}
                  setDocument={setDocument}
                  setDocId={setDocId}
                />
              )}
            </>
          )}

          {page === "verify-lexchain" && <VerificationPage />}
        </Container>
      </main>

      <footer className="lexchain-footer">
        <Container fluid="xl" className="d-flex align-items-center justify-content-between flex-wrap gap-2">
          <span>LexChain <span className="footer-divider">·</span> AI-assisted document workspace</span>
          <span>Always review generated documents before signing or relying on them.</span>
        </Container>
      </footer>
      <ToastContainer position="bottom-end" />
    </div>
  );
}

export default App;
