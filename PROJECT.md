# Santé (rewrite) — developer guide

Modern rewrite of the Santé POS: a **React + Mantine** frontend, a **FastAPI**
backend, a **SQLite** database, packaged as an **Electron** desktop app. Replaces
the legacy single-file `Sante.py` (kept at the repo root for reference until data
migration is complete in a later phase).

> Status: **All 8 phases complete** (feature-complete pending a Windows packaging build).
> Implemented: auth + roles, Inventory/Products/Recipes, Sales (stock-checked checkout),
> History, Debts, Reports (+ Excel), Dashboard (+ low-stock alerts), printable receipts,
> backup/restore, and a legacy-data importer. 144 backend tests pass. See
> [.claude/plans/](.claude/plans/) for the design spec and per-phase plans.

## Features
- **Login + roles** (admin/manager/salesman/stockman) — bcrypt-hashed passwords, JWT, role-gated nav. Default `admin`/`admin`.
- **Inventory** — add-stock (weighted avg price), edit, delete, reset, low-stock reorder levels.
- **Products / Recipes** — CRUD; recipes link products → ingredients (FK).
- **Sales** — cart, customers (+ discounts), pay-later/debt, **stock-checked transactional checkout** (rejects oversell), printable receipt.
- **Sales History / Debts** — search + date filters; mark debts paid.
- **Reports** — Daily/Weekly/Monthly/Yearly + custom range; in-app tables + **Excel export with charts**.
- **Dashboard** — today's revenue, top products (chart), low-stock alerts.
- **Settings** — DB backup (download) + restore (with auto safety-backup).
- **Legacy import** — `cd backend && .venv/bin/python -m app.migrate_legacy /path/to/old/database.db`

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
- **Windows packaging** (PyInstaller backend + electron-builder installer) — see
  [BUILD-WINDOWS.md](BUILD-WINDOWS.md). Must be built on Windows (PyInstaller cannot
  cross-compile from macOS). In a packaged build the backend serves the built frontend
  as static files and Electron loads `http://127.0.0.1:8756` (no CORS / file:// issues).
