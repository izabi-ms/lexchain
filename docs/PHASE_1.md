# LexChain Phase 1 — Stabilization and UI foundation

## Completed in this working copy

- Added environment-based configuration and a local SQLite development default; PostgreSQL remains configurable through `DATABASE_URL`.
- Removed the application-startup dependency on Ollama and local RAG initialization. NVIDIA NIM is the active provider behind a small provider boundary; Ollama code remains dormant for future work.
- Made blockchain initialization lazy and added server-side checks for the saved document text hash, successful transaction receipt, configured contract, sender, and notarization call data before persisting a client-submitted transaction.
- Removed Duck/GIF watermark and NFT experiment modules, routes, assets, and UI actions.
- Kept IPFS as a separate optional cloud-storage path using Pinata. PDFs are encrypted with a Fernet key before upload, and a local restore script verifies the plaintext SHA-256 digest after retrieval.
- Added document-storage metadata in a separate database table so the existing document table does not need new columns for IPFS metadata.
- Replaced fabricated law-firm details in the active PDF generator with neutral LexChain branding and a clear AI/legal-review disclaimer.
- Fixed several frontend workflow problems, including missing Axios dependency reliance, PDF export's missing `jsPDF` global, document-history navigation, template field labels, and verification messaging.
- Redesigned the template library, document form, history list, document workspace, navigation, and basic visual system.
- Added unit tests for AI-provider configuration and SSE parsing, encrypted IPFS upload/retrieval, and template IDs/placeholders.
- Removed local `.env` files and key files from the distributable working copy; added `.env.example` files and ignore rules.

## Checks run

- `PYTHONPATH=backend pytest -q backend/tests`: 7 passed.
- `python -m compileall -q backend`: passed.
- Frontend JavaScript/JSX syntax transpilation with the installed TypeScript compiler: 14 files passed.
- FastAPI smoke checks passed for health, the 20-template response, document save, history, status, and the expected error when NVIDIA NIM is not configured.

The container is offline and does not have PyPDF2 or the frontend npm packages installed. Therefore, the API smoke check used a minimal PyPDF2 import stub for non-PDF routes, and a full React production build plus real PDF processing were not run. Install `backend/requirements.txt` and run `npm ci` in an internet-connected development environment before relying on runtime results.

## Still required before a customer-facing MVP

- Authentication, account recovery, authorization and document ownership enforcement.
- Encrypt local document storage and define retention/deletion policies.
- Complete content-level PDF verification (hash the exact final artifact and compare it to trusted evidence); the current reference-marker check validates metadata only.
- Add database migrations and automated end-to-end/regression tests.
- Add payments and backend-enforced usage entitlements.
- Validate and review legal templates for the intended jurisdiction and target use cases.
- Complete deployment, backup/restore, monitoring, rate limiting and production secrets management.
- Test Pinata pin/unpin and restore with real credentials, and define encryption-key backup/rotation.

This phase is a development checkpoint, not a production release.
