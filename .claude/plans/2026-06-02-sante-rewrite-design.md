# Santé Rewrite — Design Spec

- **Date:** 2026-06-02
- **Status:** Draft for review
- **Author:** Claude (brainstorming session with bardia)

## 1. Goal & context

The current Santé app is a single ~1900-line Tkinter file (`Sante.py`) — a POS +
inventory manager for a single-shop, single-user food business (currency: Toman). The
file is too long and tangled to maintain. This spec defines a **from-scratch rewrite**
as a modern desktop application.

### Decisions locked during brainstorming
- **Deployment:** one computer, one user at a time. (No multi-client requirement.)
- **Architecture direction:** React frontend + backend API (chosen over modularizing
  Tkinter or a Python-only modern UI).
- **Backend:** Python / **FastAPI** — to reuse the existing pandas + openpyxl Excel
  report logic almost verbatim.
- **Scope:** Full feature parity **+ fix known issues + new features**.
- **Packaging:** **Electron** desktop app (native window + installer + icon).

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│  Electron app  (one window, one icon, double-click)   │
│                                                       │
│   ┌──────────────────────┐   HTTP/JSON   ┌─────────┐  │
│   │ Renderer (Chromium)  │ ────────────► │ FastAPI │  │
│   │  React + TypeScript  │ ◄──────────── │ backend │  │
│   └──────────────────────┘   (localhost) │ (Python)│  │
│            ▲                              └────┬────┘  │
│   ┌────────┴───────┐  spawns sidecar          │       │
│   │  Main (Node)   │ ───────────────►          ▼       │
│   └────────────────┘                     database.db   │
│                                          (SQLite)      │
└──────────────────────────────────────────────────────┘
```

Three clean layers: **React UI** (presentation) → **FastAPI** (business logic + API)
→ **SQLite** (data).

### Key packaging complication (known risk)
Electron is Node/JS; FastAPI is Python. The Electron **main process spawns the FastAPI
backend as a background "sidecar"** at startup. To avoid requiring Python on the shop
PC, the backend is bundled into a standalone executable with **PyInstaller** and shipped
inside the Electron app. This is the fiddliest part of the stack. Fallback if it proves
too painful: drop Electron for a "launcher + browser" approach (FastAPI serves the built
React on localhost). We proceed with Electron as chosen.

## 3. Tech stack

| Layer | Choice | Rationale |
|---|---|---|
| Desktop shell | Electron | Native window, installer, icon. |
| Frontend | React + TypeScript + Vite | Type safety for money/inventory math; fast builds. |
| UI components | Mantine | Production-grade tables, forms, date pickers, modals, notifications out of the box. |
| In-app charts | Recharts | Dashboard visuals. |
| Server data | TanStack Query | Fetch/cache/refetch; tables stay in sync after edits. |
| Backend | FastAPI + Uvicorn | Reuses Python report/Excel logic. |
| DB access | SQLAlchemy (ORM) | Clean per-table models; safer than scattered raw SQL. |
| Passwords | bcrypt (passlib) | Fixes plain-text passwords. |
| Excel export | openpyxl + pandas | Reuse existing chart-export logic. |
| PDF receipts | Electron print-to-PDF | Styled HTML receipt → PDF/print; no extra Python lib. |
| Backend tests | pytest + FastAPI TestClient | Cover checkout/report/auth logic. |
| Frontend tests | Vitest + React Testing Library | Component/form/table tests. |

## 4. Data model (SQLAlchemy + SQLite)

Improvement over current schema: the current `sales` table stores one row per cart line,
so "a receipt" isn't a first-class concept. Normalize into **sale header + line items**.

- **users**: id, username (unique), password_hash, role, created_at
  - roles: `admin`, `manager`, `salesman`, `stockman`
- **inventory**: id, name (unique), qty, unit, total_value, **reorder_level** (new)
  - average price derived: `total_value / qty`
- **products**: id, name (unique), price
- **recipes**: id, **product_id** (FK→products), **ingredient_id** (FK→inventory), qty
  - fixes current text-name joins and the nonexistent `product_id` reference
- **customers**: id, name (unique), discount
- **sales** (header): id, datetime, customer_id (FK, nullable), subtotal, discount_pct,
  discount_amount, total, payment_status (`Paid` | `Unpaid`)
- **sale_items**: id, sale_id (FK→sales), product_id (FK→products), product_name
  (snapshot), qty, unit_price, line_total

### Legacy migration
One-time `migrate_legacy.py` reads the old `database.db` and imports into the new schema.
Old flat `sales` rows are grouped into sale headers by (timestamp, customer); this is
approximate and documented as such. A backup of the old DB is taken first.

## 5. Backend API (FastAPI, REST/JSON)

Role enforced per-endpoint via a dependency mirroring the current `ROLE_PERMISSIONS`.

| Area | Endpoints (representative) |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Inventory | `GET /inventory?search=`, `POST /inventory`, `PATCH /inventory/{id}`, `DELETE /inventory/{id}`, `POST /inventory/reset` |
| Products | `GET/POST /products`, `PATCH/DELETE /products/{id}` |
| Recipes | `GET /recipes?product_id=`, `POST /recipes`, `PATCH/DELETE /recipes/{id}` |
| Customers | `GET/POST /customers`, `PATCH/DELETE /customers/{id}` |
| Sales | `POST /sales` (checkout: stock-checked + transactional), `GET /sales?search=&start=&end=`, `GET /sales/{id}` (receipt) |
| Debts | `GET /debts`, `POST /debts/{sale_id}/pay` |
| Reports | `GET /reports?type=&start=&end=`, `GET /reports/export.xlsx` |
| Dashboard | `GET /dashboard` |
| Backup | `GET /backup`, `POST /restore` |
| Users | `GET/POST /users`, `PATCH/DELETE /users/{id}` (admin/manager only) |

### Role → access (parity with current app)
| Role | Areas |
|---|---|
| admin / manager | all |
| salesman | Sales, Reports, Debts |
| stockman | Inventory |

## 6. Project structure

```
sante/
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app, CORS, routers, startup
│       ├── db.py              # SQLAlchemy engine/session, SQLite path
│       ├── models.py          # ORM models
│       ├── schemas.py         # Pydantic request/response models
│       ├── auth.py            # login, bcrypt hashing, token, role dependency
│       ├── routers/           # inventory, products, recipes, customers, sales,
│       │                      #   debts, reports, dashboard, users, backup
│       ├── services/          # checkout.py, reporting.py, excel_export.py
│       └── migrate_legacy.py  # one-time import from old database.db
├── frontend/
│   └── src/
│       ├── api/               # typed client per resource + TanStack Query hooks
│       ├── auth/              # login screen, auth context, role guard
│       ├── components/        # DataTable, FormModal, ConfirmDialog, ...
│       ├── pages/             # Dashboard, Inventory, Products, Recipes, Sales,
│       │                      #   History, Debts, Reports, Users
│       └── layout/            # app shell + role-based nav
└── electron/
    ├── main.js                # window + spawn FastAPI sidecar + health check
    ├── preload.js             # IPC bridge (print-to-PDF, backup/restore dialogs)
    └── electron-builder config
```

## 7. New features

1. **Dashboard + low-stock alerts** — `GET /dashboard` returns today's revenue, sale
   count, top products by qty, and ingredients where `qty ≤ reorder_level`. Recharts
   visuals. `reorder_level` editable per ingredient.
2. **Edit + search everywhere** — every list endpoint accepts `?search=`; PATCH
   endpoints enable in-place edits; Mantine tables provide search + edit UI.
3. **Date-range reports + PDF receipts** — Reports page has a date-range picker plus
   daily/weekly/monthly/yearly presets. Receipts render as styled HTML and export via
   Electron print-to-PDF / print dialog.
4. **Backup & restore** — Electron file dialogs. Backup downloads/copies the SQLite DB
   (timestamped). Restore takes an automatic safety-backup first, behind a confirm dialog.

## 8. Fixes folded in (from "parity + fix known issues")

- Passwords hashed with bcrypt (no more plain text).
- Checkout blocks negative stock (validates each ingredient before committing).
- Input validation via Pydantic (backend) + form validation (frontend).
- Remove the duplicated `show_login` logic.
- Proper foreign keys for recipes (product/ingredient).
- Keep checkout transactional (existing behavior, preserved).

## 9. Error handling

- **Backend:** Pydantic validation; consistent JSON error bodies; correct HTTP codes;
  401/403 for auth/role failures.
- **Frontend:** TanStack Query error states; Mantine notifications for success/error;
  confirm dialogs for destructive actions (delete, reset, restore).
- **Electron:** health-check the backend sidecar before showing the UI; clear error
  screen if the backend fails to start.

## 10. Testing strategy

- **Backend (primary, TDD):** pytest + FastAPI TestClient against a temp SQLite DB —
  checkout stock math, report aggregations, auth/role enforcement, migration import.
- **Frontend:** Vitest + React Testing Library for forms/tables; optional Playwright
  e2e later.

## 11. Phased build plan

0. **Scaffold** — backend + React/Mantine shell + Electron spawning the sidecar; one
   trivial endpoint proving the end-to-end pipeline.
1. **Auth + roles + Users** — login, hashing, role-gated navigation.
2. **Inventory + Products + Recipes** — CRUD + search + edit.
3. **Sales** — cart, stock-checked checkout, customers, debts creation.
4. **History + Debts** — sales history list, mark-as-paid.
5. **Reports** — date-range + in-app view + Excel export (reuse openpyxl).
6. **Dashboard + low-stock alerts**.
7. **PDF receipts + Backup/restore**.
8. **Legacy data migration + packaging** — PyInstaller backend, electron-builder installer.

## 12. Confirmed decisions & remaining defaults

- Shop PC OS: **Windows** (confirmed) — Electron builds a Windows installer; printing via
  Electron print-to-PDF / print dialog.
- Version control: **git initialized** 2026-06-02 with a `.gitignore`.
- TypeScript vs JavaScript: **TypeScript** (default; not objected to).
- UI library: **Mantine** (default; alt: Ant Design).
- DB layer: **SQLAlchemy ORM** (default; alt: raw `sqlite3`).
