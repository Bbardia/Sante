# Santé (rewrite) — developer guide

Modern rewrite of the Santé POS: a **React + Mantine** frontend, a **FastAPI**
backend, a **SQLite** database, packaged as an **Electron** desktop app. Replaces
the legacy single-file `Sante.py` (kept at the repo root for reference until data
migration is complete in a later phase).

> Status: **Phase 0 (scaffold)** complete — the three layers are wired and prove the
> pipeline end-to-end (Electron spawns the backend, the React UI reads `/health`).
> Feature work begins in Phase 1. See [.claude/plans/](.claude/plans/) for the design
> spec and per-phase plans.

## Layout
```
backend/    FastAPI + SQLAlchemy + SQLite (port 8756)
frontend/   React + TypeScript + Vite + Mantine + TanStack Query (dev port 5173)
electron/   Electron shell that spawns the backend and loads the UI
Sante.py    legacy app (reference only)
```

## One-time setup
```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
# frontend
cd frontend && npm install && cd ..
# electron
cd electron && npm install && cd ..
```

## Run in development (macOS)
Two terminals:

```bash
# Terminal 1 — frontend dev server
cd frontend && npm run dev
```
```bash
# Terminal 2 — Electron (spawns the backend automatically)
cd electron && npm start
```
An Electron window opens showing **Santé** with a green **ok** backend-health badge.
Closing the window stops the backend sidecar.

## Run backend tests
```bash
cd backend && .venv/bin/python -m pytest -v
```

## Notes
- Ports: backend **8756**, Vite dev **5173**. If `npm start` reports the backend
  failed, check nothing else is using 8756 (`lsof -i :8756`).
- The Electron health check uses Node's built-in `http` (not global `fetch`), so it
  works regardless of the installed Electron/Node version.
- **Windows packaging** (PyInstaller backend + electron-builder installer) is a later
  phase and must be built on Windows / CI — PyInstaller cannot cross-compile from macOS.
