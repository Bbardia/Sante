# Building the Windows Installer

> **Important:** PyInstaller cannot cross-compile. All steps below must be run on a **Windows** machine.

## Prerequisites

- Python 3.11+ (added to PATH)
- Node.js 18+ and npm
- Git (to clone the repo)

---

## 1. Build the Python backend executable

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller sante-backend.spec
```

This produces `backend\dist\sante-backend.exe`.

> **Note on the database:** At runtime the backend creates `database.db` next to the executable.
> In a packaged Electron app the exe lives inside `resources\backend\`, so the database will be
> created at `resources\backend\database.db` on first run.

---

## 2. Build the frontend SPA

```cmd
cd frontend
npm install
npm run build
```

This produces the static SPA in `frontend\dist\`.

---

## 3. Build the Windows installer

```cmd
cd electron
npm install
npm run dist
```

This runs `electron-builder --win` and produces an NSIS installer in `electron\release\`.

The installer bundles:
- `resources\backend\sante-backend.exe` — the PyInstaller-packaged FastAPI server
- `resources\frontend\` — the built Vite/React SPA (served by the backend via `SANTE_STATIC_DIR`)

---

## How it works at runtime

1. Electron spawns `sante-backend.exe` with `SANTE_STATIC_DIR` pointing to `resources\frontend\`.
2. The FastAPI backend serves the SPA from that directory (mounted last, so API routes take priority).
3. Electron loads `http://127.0.0.1:8756` — the UI is same-origin with the API, no CORS needed.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Backend failed to start" screen | `sante-backend.exe` missing or failed to launch; check Windows Event Viewer |
| Blank/white screen | Frontend dist not copied correctly into resources |
| API 500 errors | Check if `database.db` is writable in the resources directory |
