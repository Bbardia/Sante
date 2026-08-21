# Santé Rewrite — Phase 0: Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable Electron desktop app that spawns a FastAPI (Python) backend as a sidecar and renders a React + Mantine UI which successfully calls a backend `/health` endpoint — proving the full three-layer pipeline end-to-end.

**Architecture:** Three folders at the repo root — `backend/` (FastAPI + SQLAlchemy + SQLite), `frontend/` (React + TypeScript + Vite + Mantine + TanStack Query), `electron/` (Electron main process that spawns the backend and loads the frontend). In development everything runs on the Mac via a Python venv and the Vite dev server; production Windows packaging (PyInstaller + electron-builder) is deferred to Phase 8.

**Tech Stack:** Python 3, FastAPI, Uvicorn, SQLAlchemy, pytest, httpx; Node, React 18, TypeScript, Vite, Mantine v7, TanStack Query; Electron.

**Reference spec:** [2026-06-02-sante-rewrite-design.md](./2026-06-02-sante-rewrite-design.md)

**Conventions:**
- The new app lives in the existing git repo at `/Users/bardia/Desktop/Behrad`. The legacy `Sante.py` stays at the root as reference until data migration is verified in a later phase.
- Backend dev server port: **8756** (uncommon, to avoid clashes). Vite dev port: **5173**.
- Commit after every task. Use Conventional Commit messages.

---

## File structure created in this phase

```
backend/
├── requirements.txt          # backend Python deps
├── app/
│   ├── __init__.py
│   ├── db.py                 # SQLAlchemy engine/session/Base + get_db
│   └── main.py               # FastAPI app + CORS + /health
└── tests/
    ├── __init__.py
    └── test_health.py        # TestClient test for /health
frontend/                     # created by Vite react-ts template
├── src/
│   ├── api/client.ts         # typed fetch client (getHealth)
│   ├── main.tsx              # MantineProvider + QueryClientProvider
│   └── App.tsx               # renders backend health status
├── postcss.config.cjs        # Mantine PostCSS
└── .env.development          # VITE_API_BASE
electron/
├── package.json              # electron app manifest + scripts
├── main.js                   # spawn backend sidecar + load frontend
└── preload.js                # minimal contextBridge
PROJECT.md                    # how to run the new app in dev
```

---

## Task 1: Backend skeleton with health endpoint (TDD)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Create backend folders**

Run:
```bash
mkdir -p backend/app backend/tests
```

- [ ] **Step 2: Write `backend/requirements.txt`**

```
fastapi
uvicorn[standard]
sqlalchemy
passlib[bcrypt]
pandas
openpyxl
python-multipart
# dev / test
pytest
httpx
```

- [ ] **Step 3: Create the virtualenv and install deps**

Run:
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
cd ..
```
Expected: installs complete with no errors.

- [ ] **Step 4: Write `backend/app/__init__.py` and `backend/tests/__init__.py`**

Both files are empty (package markers). Create them empty.

- [ ] **Step 5: Write `backend/app/db.py`**

```python
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "database.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 6: Write the failing test `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
```

- [ ] **Step 7: Run the test to verify it fails**

Run:
```bash
cd backend && .venv/bin/python -m pytest tests/test_health.py -v; cd ..
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'` (main.py not created yet).

- [ ] **Step 8: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Santé API")

# Dev CORS: allow the Vite dev server. Tightened in a later phase.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 9: Run the test to verify it passes**

Run:
```bash
cd backend && .venv/bin/python -m pytest tests/test_health.py -v; cd ..
```
Expected: PASS (1 passed).

- [ ] **Step 10: Manually verify the server runs**

Run:
```bash
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8756 &
sleep 2 && curl -s http://localhost:8756/health && echo && kill %1; cd ..
```
Expected: prints `{"status":"ok"}`.

- [ ] **Step 11: Commit**

```bash
git add backend/requirements.txt backend/app backend/tests
git commit -m "feat(backend): FastAPI skeleton with /health and SQLAlchemy db setup"
```

---

## Task 2: Frontend skeleton (Vite + Mantine + TanStack Query) showing health

**Files:**
- Create: `frontend/` (via Vite template)
- Create: `frontend/src/api/client.ts`
- Create: `frontend/.env.development`
- Create: `frontend/postcss.config.cjs`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Scaffold the Vite React-TS app**

Run:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install && cd ..
```
Expected: `frontend/` created, dependencies installed.

- [ ] **Step 2: Install Mantine, TanStack Query, and Mantine PostCSS**

Run:
```bash
cd frontend
npm install @mantine/core @mantine/hooks @tanstack/react-query
npm install -D postcss postcss-preset-mantine postcss-simple-vars
cd ..
```

- [ ] **Step 3: Write `frontend/postcss.config.cjs`**

```js
module.exports = {
  plugins: {
    'postcss-preset-mantine': {},
    'postcss-simple-vars': {
      variables: {
        'mantine-breakpoint-xs': '36em',
        'mantine-breakpoint-sm': '48em',
        'mantine-breakpoint-md': '62em',
        'mantine-breakpoint-lg': '75em',
        'mantine-breakpoint-xl': '88em',
      },
    },
  },
};
```

- [ ] **Step 4: Write `frontend/.env.development`**

```
VITE_API_BASE=http://localhost:8756
```

- [ ] **Step 5: Write `frontend/src/api/client.ts`**

```ts
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8756";

export interface Health {
  status: string;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`health request failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 6: Overwrite `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@mantine/core/styles.css";
import App from "./App";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
```

- [ ] **Step 7: Overwrite `frontend/src/App.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { Container, Title, Text, Badge, Loader } from "@mantine/core";
import { getHealth } from "./api/client";

export default function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  return (
    <Container p="xl">
      <Title order={1}>Santé</Title>
      <Text mt="md">
        Backend status:{" "}
        {isLoading && <Loader size="xs" />}
        {isError && <Badge color="red">unreachable</Badge>}
        {data && <Badge color="green">{data.status}</Badge>}
      </Text>
    </Container>
  );
}
```

- [ ] **Step 8: Verify the frontend talks to the backend**

Run (two terminals, or background the backend):
```bash
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8756 &
cd ../frontend && npm run dev
```
Open http://localhost:5173 in a browser.
Expected: page shows "Santé" and a green `ok` badge. Then stop both (`kill %1`, Ctrl-C).

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat(frontend): Vite + Mantine + TanStack Query shell showing backend health"
```

---

## Task 3: Electron shell that spawns the backend and loads the frontend

**Files:**
- Create: `electron/package.json`
- Create: `electron/main.js`
- Create: `electron/preload.js`

- [ ] **Step 1: Create the electron folder and manifest `electron/package.json`**

```json
{
  "name": "sante-desktop",
  "version": "0.0.1",
  "description": "Santé POS desktop shell",
  "main": "main.js",
  "scripts": {
    "start": "electron ."
  },
  "devDependencies": {
    "electron": "^31.0.0"
  }
}
```

- [ ] **Step 2: Install electron**

Run:
```bash
cd electron && npm install && cd ..
```

- [ ] **Step 3: Write `electron/preload.js`**

```js
const { contextBridge } = require("electron");

// Minimal bridge for now; expanded in later phases (print-to-PDF, file dialogs).
contextBridge.exposeInMainWorld("sante", {
  version: "0.0.1",
});
```

- [ ] **Step 4: Write `electron/main.js`**

```js
const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

const BACKEND_PORT = 8756;
const DEV_URL = "http://localhost:5173";

let backendProcess = null;

function startBackend() {
  // Dev: run uvicorn from the backend venv (macOS/Linux path).
  const pythonBin = path.join(__dirname, "..", "backend", ".venv", "bin", "python");
  backendProcess = spawn(
    pythonBin,
    ["-m", "uvicorn", "app.main:app", "--port", String(BACKEND_PORT)],
    { cwd: path.join(__dirname, "..", "backend"), stdio: "inherit" },
  );
  backendProcess.on("error", (err) => {
    console.error("Failed to start backend:", err);
  });
}

async function waitForBackend() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch(`http://localhost:${BACKEND_PORT}/health`);
      if (res.ok) return true;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

async function createWindow() {
  startBackend();
  const healthy = await waitForBackend();

  const win = new BrowserWindow({
    width: 1400,
    height: 850,
    webPreferences: { preload: path.join(__dirname, "preload.js") },
  });

  if (healthy) {
    win.loadURL(DEV_URL);
  } else {
    win.loadURL(
      "data:text/html," +
        encodeURIComponent(
          "<h1>Backend failed to start</h1><p>Check the terminal logs.</p>",
        ),
    );
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  app.quit();
});
```

- [ ] **Step 5: Commit**

```bash
git add electron
git commit -m "feat(electron): desktop shell that spawns FastAPI sidecar and loads the UI"
```

---

## Task 4: End-to-end dev run + project README

**Files:**
- Create: `PROJECT.md`

- [ ] **Step 1: Write `PROJECT.md`**

````markdown
# Santé (rewrite) — developer guide

Modern rewrite of the Santé POS: React + Mantine frontend, FastAPI backend,
SQLite database, packaged as an Electron desktop app. Replaces the legacy
single-file `Sante.py` (kept at the repo root for reference until data
migration is complete).

## One-time setup
```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
# frontend
cd frontend && npm install && cd ..
# electron
cd electron && npm install && cd ..
```

## Run in development (Mac)
Terminal 1 — frontend dev server:
```bash
cd frontend && npm run dev
```
Terminal 2 — Electron (spawns the backend automatically):
```bash
cd electron && npm start
```
An Electron window opens showing the app with a green backend-health badge.

## Run backend tests
```bash
cd backend && .venv/bin/python -m pytest -v
```

## Notes
- Backend dev port: 8756. Vite dev port: 5173.
- Windows packaging (PyInstaller backend + electron-builder installer) is a
  later phase and must be built on Windows / CI (PyInstaller can't cross-compile).
````

- [ ] **Step 2: Full end-to-end verification**

Run frontend (terminal 1): `cd frontend && npm run dev`
Run electron (terminal 2): `cd electron && npm start`
Expected: an Electron window titled by the OS opens, shows "Santé" and a green `ok` badge (backend reached through the spawned sidecar). Close the window; confirm the backend process is killed (no lingering uvicorn).

- [ ] **Step 3: Commit**

```bash
git add PROJECT.md
git commit -m "docs: add developer guide for the rewrite (PROJECT.md)"
```

---

## Phase 0 done — definition of done

- `cd backend && .venv/bin/python -m pytest -v` → all green.
- `cd electron && npm start` (with Vite running) → window shows green backend health badge.
- Closing the window terminates the backend sidecar.
- Four commits landed (backend, frontend, electron, docs).

## Roadmap — subsequent plans (one per phase)

1. **Phase 1:** Auth + roles + Users (login, bcrypt hashing, role-gated nav).
2. **Phase 2:** Inventory + Products + Recipes (CRUD + search + edit).
3. **Phase 3:** Sales (cart, stock-checked checkout, customers, debts).
4. **Phase 4:** History + Debts.
5. **Phase 5:** Reports (date-range + Excel export reusing openpyxl).
6. **Phase 6:** Dashboard + low-stock alerts.
7. **Phase 7:** PDF receipts + Backup/restore.
8. **Phase 8:** Legacy data migration + Windows packaging (PyInstaller + electron-builder).
