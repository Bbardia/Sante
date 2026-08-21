# Project: Santé

Project context for Claude Code. This file is loaded automatically at the start of
each session, so it acts as durable project memory.

## What this is
A single-file desktop **POS + inventory management** app for a small food/beverage
business. Built with **Tkinter** (GUI), **SQLite** (`database.db`), **pandas** and
**openpyxl** (reports/Excel export). Currency is **Toman**.

Everything lives in [Sante.py](../Sante.py). See [README.md](../README.md) for the
full feature/setup overview.

## How to run
```bash
pip install -r requirements.txt   # pandas, openpyxl
python3 Sante.py
```
Default login: `admin` / `admin`.

## Architecture notes (important for edits)
- **Single file, module-level globals.** Widgets, business logic, and DB access are
  all top-level in `Sante.py`. There are no functions/classes wrapping the app —
  ordering of statements matters. Some functions reference widgets defined later and
  guard with `globals()` / try-except.
- **Database:** one SQLite connection (`conn`) + cursor (`c`) shared globally. Tables:
  `inventory`, `products`, `recipes`, `sales`, `customers`, `users`. Schema is created
  with `CREATE TABLE IF NOT EXISTS` and migrated with best-effort `ALTER TABLE` in
  try/except — keep this pattern when adding columns.
- **Tabs** are built sequentially; role-based visibility via `ROLE_PERMISSIONS` and
  `apply_permissions()`.
- **`show_login` is defined twice** — the second definition (with attempt-limiting)
  wins. Be careful not to "fix" one without accounting for the other.

## Known gotchas / tech debt (don't be surprised)
- Passwords stored in **plain text**; default admin is `admin`/`admin`.
- `tkinter` needs the system Tk binding (`brew install python-tk` on macOS) — the
  current Homebrew Python 3.14 here is missing `_tkinter`.
- Checkout can drive inventory **negative** (no stock check).
- References to `sales_discount_entry` and a `recipes.product_id` column exist but the
  widgets/columns aren't defined; guarded paths fail gracefully.

## Conventions for working here
- This repo is **not yet a git repository**. Ask before `git init` if version control
  is wanted.
- Prefer minimal, surgical edits that match the existing flat/global style unless a
  refactor is explicitly requested.
- Plans produced by the Superpowers `writing-plans` skill go in [plans/](./plans/).
- Project-local skills (if any) go in [skills/](./skills/).
