# LexChain backend

FastAPI backend for AI-assisted document drafting, document history, blockchain hash recording, PDF export, and optional encrypted IPFS backup.

## Requirements

- Python 3.11 or newer
- NVIDIA NIM API key and model name for AI drafting
- Optional: MetaMask-compatible Ethereum RPC endpoint and deployed LexChain contract
- Optional: Pinata account for encrypted IPFS backups

## Local setup (PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set at least:

```dotenv
AI_PROVIDER=nvidia_nim
NVIDIA_NIM_API_KEY=your_nvidia_nim_key
NVIDIA_NIM_MODEL=your_available_nim_model_id
```

The backend uses a local SQLite database by default for development. To use PostgreSQL, set `DATABASE_URL` to a valid SQLAlchemy PostgreSQL URL. Existing PostgreSQL installations should keep their own database URL and credentials in the local `.env` file.

Start the backend from the `backend` directory:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: <http://127.0.0.1:8000/docs>
Health check: <http://127.0.0.1:8000/health>

## NVIDIA NIM

The application uses NVIDIA NIM's OpenAI-compatible chat-completions endpoint. Keep API credentials on the backend only. Configure `NVIDIA_NIM_BASE_URL`, `NVIDIA_NIM_API_KEY`, and `NVIDIA_NIM_MODEL` in `.env`. The application does not initialize Ollama or local embeddings during startup. Ollama remains a future option and is intentionally disabled in this phase.

## Optional encrypted IPFS backup

The Pinata adapter is optional and disabled until credentials and an encryption key are configured:

```dotenv
IPFS_PROVIDER=pinata
PINATA_JWT=your_pinata_jwt
IPFS_GATEWAY_URL=https://gateway.pinata.cloud/ipfs
IPFS_ENCRYPTION_KEY=your_fernet_key
```

Generate a Fernet key with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

LexChain encrypts the PDF before uploading it to IPFS. The encryption key must remain private and must be backed up securely; losing it means encrypted files cannot be recovered. A CID is not access control, and IPFS availability depends on pinning/provider retention. The local prototype does not yet have user-account authorization, so do not use it for real confidential customer documents until the authentication and ownership phase is completed.

## Optional blockchain configuration

To test blockchain operations, configure the RPC URL, deployed contract address, service account address, and private key in `.env`. The private key must be a dedicated test wallet with limited funds. The blockchain service initializes lazily and does not block application startup when these values are absent.

## Important development status

- Database tables are created automatically for the local baseline. Database migrations still need to be introduced before shared/production deployments.
- PDF reference-marker verification currently checks metadata only. Full content-integrity verification must be completed before marketing this feature as cryptographic document verification.
- Authentication, authorization, payment enforcement, and production deployment are not yet implemented.
