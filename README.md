# Santé

A desktop **point-of-sale (POS) and inventory management** application for a small
food/beverage business. It is a single-file Python program built with **Tkinter**
(GUI) and **SQLite** (local database), with **pandas** + **openpyxl** powering
report generation and Excel export.

Currency is displayed in **Toman**.

---

## Features

The app is organized as a tabbed window. Tabs are shown/hidden based on the
logged-in user's role (see [Roles & permissions](#roles--permissions)).

| Tab | What it does |
|-----|--------------|
| **Inventory** | Add/delete ingredients with quantity, unit, and price. Tracks a running **average price** per ingredient (total value ÷ quantity). Supports a full reset of quantities/values. |
| **Products** | Define sellable products and their prices. |
| **Recipes** | Link a product to the ingredients (and amounts) it consumes — a bill of materials. Selling a product automatically deducts its recipe ingredients from inventory. |
| **Sales** | Build a cart, attach a customer, apply a discount, and check out. Supports **"Pay Later (Debt)"** for credit sales and prints a receipt to the system printer. |
| **Sales History** | Read-only list of all sales with total revenue. |
| **Debts** | Lists unpaid sales; mark a debt as **Paid**. |
| **Reports** | Daily / Weekly / Monthly / Yearly summaries (revenue, paid vs. unpaid, inventory consumption, customer breakdown, unpaid bills) with **Excel export** including bar/pie charts. |
| **Users** | Create/update/delete users and assign roles. |

---

## Tech stack

- **Python 3** (developed against CPython 3.14)
- **Tkinter / ttk** — desktop GUI
- **SQLite** (`sqlite3`) — local file database, auto-created as `database.db`
- **pandas** — tabular data for reports/export
- **openpyxl** — `.xlsx` writing with embedded charts

---

## Requirements & installation

### 1. Python 3
Ensure Python 3 is installed: `python3 --version`

### 2. System Tk (for the GUI)
Tkinter ships with CPython but relies on the system **Tk** binding. If
`python3 -c "import tkinter"` fails with `No module named '_tkinter'`, install it:

- **macOS (Homebrew):** `brew install python-tk`
- **Debian/Ubuntu:** `sudo apt install python3-tk`
- **Windows:** included with the official python.org installer

### 3. Python packages
```bash
pip install -r requirements.txt
```
This installs `pandas` and `openpyxl`. (Excel export will fail until `openpyxl`
is installed.)

---

## Running the app

```bash
python3 Sante.py
```

On first launch the app:
1. Creates `database.db` next to the script (or next to the executable if frozen
   with PyInstaller).
2. Seeds a default admin account.
3. Shows a **login window**.

### Default login
| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin`  | admin |

> ⚠️ **Security:** the default credentials are `admin` / `admin`, and passwords are
> stored in the database **in plain text**. Change the admin password and add real
> users before any real-world use. After 3 failed login attempts the app closes.

---

## Roles & permissions

Tab access is controlled by role:

| Role | Accessible tabs |
|------|-----------------|
| **admin** / **manager** | Inventory, Products, Recipes, Sales, Reports, Debts, Users |
| **salesman** | Sales, Reports, Debts |
| **stockman** | Inventory |

---

## Data & files

| File | Purpose |
|------|---------|
| `Sante.py` | The entire application. |
| `database.db` | SQLite database (auto-created). Holds inventory, products, recipes, sales, customers, and users. |
| `receipt_to_print.txt` | Last generated receipt, written before being sent to the printer. |
| `*.xlsx` | Exported reports (you choose the path via a save dialog). |

> 💾 **Backups:** all business data lives in `database.db`. Back it up regularly.

---

## Notes & known limitations

- **Single-file, global-state design.** The UI, business logic, and database access
  all live in `Sante.py` using module-level globals. It works but is hard to test
  and extend.
- **Plain-text passwords** (no hashing).
- **Schema is created/migrated inline** via `CREATE TABLE IF NOT EXISTS` and
  best-effort `ALTER TABLE ... ADD COLUMN` wrapped in try/except.
- **Recipe consumption** can drive inventory negative — there is no stock check at
  checkout.
- **Printing** uses the OS default printer (`os.startfile(..., "print")` on Windows,
  `lpr` on macOS/Linux).
- The Reports tab references a `sales_discount_entry` widget and a `recipes.product_id`
  column that are not defined in this file; those code paths are guarded with
  try/except or `globals()` checks, so they fail gracefully.

---

## Project layout

```
Behrad/
├── Sante.py            # the application
├── requirements.txt    # Python dependencies
├── README.md           # this file
├── database.db         # created on first run (not committed)
└── .claude/            # Claude Code workspace config (see .claude/CLAUDE.md)
    ├── CLAUDE.md        # project context loaded each session
    ├── plans/          # implementation plans (Superpowers writing-plans skill)
    └── skills/         # project-local skills
```
