# Santé

A **point-of-sale (POS) and inventory management** application for a small
food/beverage business. Modern rewrite of the original single-file Tkinter app:
a **React + TypeScript** frontend, a **FastAPI** backend, a **SQLite** database,
packaged as an **Electron** desktop app.

Currency is displayed in **Toman**.

> The legacy single-file app still lives at [`Sante.py`](Sante.py) for reference
> until data migration is fully retired. **It is not the app you run** — use the
> instructions below.

---

## Quick start (one command)

A [`Makefile`](Makefile) runs the whole stack. You need **Python 3**, **Node.js**,
and **npm** installed.

```bash
make setup     # one-time: create the Python venv, install backend + frontend deps
make seed      # optional: reset the DB and load demo data (sample inventory/sales)
make demo      # build the UI and serve the whole app on one port
```

Then open **http://localhost:8756** and log in with **`admin` / `admin`**.

Run `make help` to see every command:

| Command | What it does |
|---|---|
| `make setup` | One-time install: Python venv + backend deps + `npm install` the frontend |
| `make dev` | Run backend (`:8756`) **and** the Vite hot-reload dev server (`:5173`) together — best for development |
| `make demo` | Build the SPA and have the backend serve it on **one port** → `http://localhost:8756` — best for showing the app |
| `make demo-lan` | Same as `demo`, but reachable from **other devices on your WiFi** (phones/tablets); prints the LAN URL |
| `make seed` | Reset the dev database and load realistic demo data |
| `make test` | Run backend (pytest) + frontend (vitest) test suites |
| `make build` | Build the frontend into `frontend/dist` |
| `make clean` | Remove the venv, `node_modules`, and build output |

- **`make dev`** is the developer flow: the frontend at `:5173` calls the backend
  at `:8756` with hot reload. Ctrl-C stops both.
- **`make demo` / `make demo-lan`** are the demo flow: the frontend is built and
  served by the backend itself, so everything lives on a single URL with no CORS
  setup — ideal for showing people the app on this machine or across the network.

---

## Tech stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + TypeScript + Vite + [Mantine](https://mantine.dev) UI + TanStack Query + Recharts (dev port **5173**) |
| **Backend** | FastAPI + SQLAlchemy 2 + SQLite, JWT auth with **bcrypt-hashed** passwords, openpyxl for Excel export (port **8756**) |
| **Desktop** | Electron shell that spawns the backend and loads the UI |
| **Tests** | pytest (backend) · Vitest + React Testing Library (frontend) |

The database lives at `backend/database.db` (auto-created on first run, **not**
committed).

---

## Features

The UI is a single-page app with role-gated navigation.

| Page | What it does |
|------|--------------|
| **Dashboard** | Today's revenue and sales count, top products chart, low-stock alerts. |
| **Inventory** | Add stock (tracks a weighted **average price** per ingredient), edit, delete, reset, and set low-stock reorder levels. |
| **Products** | Define sellable products and their prices. |
| **Recipes** | Link a product to the ingredients (and amounts) it consumes — a bill of materials. Checkout deducts a product's recipe from inventory. |
| **Sales** | Build a cart, attach a customer (with discount), apply a discount, and check out. Supports **Pay Later (debt)** and a printable receipt. Checkout is **stock-checked and transactional** — it rejects oversell. |
| **Sales History** | Search + date-filtered list of all sales. |
| **Debts** | Lists unpaid sales; mark a debt as **Paid**. |
| **Reports** | Daily / Weekly / Monthly / Yearly + custom range summaries with in-app tables and **Excel export** (with charts). |
| **Users** | Create/update/delete users and assign roles (admin only). |
| **Settings** | Download a database backup and restore from one (with an automatic safety backup). |

---

## Roles & permissions

Navigation is gated by the logged-in user's role:

| Role | Accessible pages |
|------|-----------------|
| **admin** | All pages (incl. Users + Settings) |
| **manager** | Dashboard, Inventory, Products, Recipes, Sales, Sales History, Debts, Reports |
| **salesman** | Dashboard, Sales, Sales History, Debts, Reports |
| **stockman** | Inventory |

> ⚠️ **Security:** the default credentials are `admin` / `admin`. Passwords are
> bcrypt-hashed and auth uses JWTs, but you should still change the admin password
> and create real users before any real-world use. The app is built for a trusted
> local network, not public internet exposure.

---

## Manual setup (without `make`)

<details>
<summary>If you prefer to run the pieces yourself</summary>

```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
# frontend
cd frontend && npm install && cd ..
```

Run in development (two terminals):

```bash
# Terminal 1 — backend
cd backend && .venv/bin/python run_server.py        # http://localhost:8756

# Terminal 2 — frontend dev server
cd frontend && npm run dev                           # http://localhost:5173
```

Run the desktop (Electron) shell, which spawns the backend automatically:

```bash
cd electron && npm install && npm start
```

</details>

See [PROJECT.md](PROJECT.md) for the full developer guide and
[BUILD-WINDOWS.md](BUILD-WINDOWS.md) for packaging a Windows installer
(PyInstaller backend + electron-builder).

---

## Tests

```bash
make test                              # both suites
# or individually:
cd backend  && .venv/bin/python -m pytest
cd frontend && npm test
```

---

## Migrating data from the legacy app

Import data from an old Tkinter-era `database.db`:

```bash
cd backend && .venv/bin/python -m app.migrate_legacy /path/to/old/database.db
```

---

## Project layout

```
Sante/
├── Makefile            # one-command runner (setup / dev / demo / seed / test)
├── backend/            # FastAPI + SQLAlchemy + SQLite (port 8756)
│   ├── app/            #   routers, models, services, security
│   ├── tests/          #   pytest suite
│   ├── seed_demo.py    #   reset + seed demo data
│   └── run_server.py   #   uvicorn entrypoint
├── frontend/           # React + TypeScript + Vite + Mantine (dev port 5173)
│   └── src/            #   pages, api client, auth, components
├── electron/           # Electron shell that spawns the backend + loads the UI
├── Sante.py            # legacy single-file Tkinter app (reference only)
├── PROJECT.md          # full developer guide
└── BUILD-WINDOWS.md    # Windows packaging instructions
```

> 💾 **Backups:** all business data lives in `backend/database.db`. Back it up
> regularly, or use the in-app **Settings → Backup**.
