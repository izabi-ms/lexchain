# LexChain frontend

React frontend for the LexChain development MVP.

## Local setup

Requirements: Node.js 20 or newer and npm.

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

Set `REACT_APP_BACKEND_URL` to the FastAPI URL. Set `REACT_APP_CONTRACT_ADDRESS` only when testing blockchain notarization against the matching deployed contract and network.

Start the frontend:

```powershell
npm start
```

The app currently supports document templates, streaming AI generation, editing, PDF export, wallet-based hash recording, document history, and a basic PDF metadata-marker check. This verification check is not yet full content-integrity proof. Do not use the prototype for confidential customer documents until authentication and ownership controls are implemented.
