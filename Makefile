# Santé — one-command runner for the React + FastAPI app.
#
#   make setup       install backend (venv) + frontend dependencies  (run once)
#   make seed        reset the dev DB and load demo data (optional but recommended)
#   make dev         run backend (:8756) + Vite dev server (:5173) with hot reload
#   make demo        build the SPA and serve the whole app on ONE port -> http://localhost:8756
#   make demo-lan    same as demo, but reachable from other devices on your WiFi
#   make test        run backend (pytest) + frontend (vitest) tests
#
# Default login: admin / admin.

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
PORT     := 8756

.DEFAULT_GOAL := help
.PHONY: help setup dev demo demo-lan build seed test test-backend test-frontend clean

help: ## Show this help
	@echo "Santé — available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend (venv) + frontend dependencies (run once)
	@echo "→ Creating backend virtualenv + installing Python deps..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip >/dev/null
	$(PIP) install -r $(BACKEND)/requirements.txt
	@echo "→ Installing frontend dependencies..."
	cd $(FRONTEND) && npm install
	@echo "✓ Setup complete. Next: 'make seed' (optional demo data), then 'make dev' or 'make demo'."

dev: ## Run backend (:8756) + frontend dev server (:5173) together (Ctrl-C stops both)
	@test -x $(PY) || { echo "✗ Backend venv missing — run 'make setup' first."; exit 1; }
	@test -d $(FRONTEND)/node_modules || { echo "✗ Frontend deps missing — run 'make setup' first."; exit 1; }
	@echo "→ Backend  http://localhost:$(PORT)     Frontend  http://localhost:5173"
	@echo "  (login: admin / admin — Ctrl-C stops both)"
	@trap 'kill 0' EXIT INT TERM; \
		( cd $(BACKEND)  && exec .venv/bin/python run_server.py ) & \
		( cd $(FRONTEND) && exec npm run dev ) & \
		wait

build: ## Build the frontend SPA into frontend/dist
	@test -d $(FRONTEND)/node_modules || { echo "✗ Frontend deps missing — run 'make setup' first."; exit 1; }
	cd $(FRONTEND) && npm run build

demo: build ## Build + serve the whole app on one port -> http://localhost:8756
	@test -x $(PY) || { echo "✗ Backend venv missing — run 'make setup' first."; exit 1; }
	@echo "→ Santé running at http://localhost:$(PORT)  (login: admin / admin — Ctrl-C to stop)"
	@cd $(BACKEND) && SANTE_STATIC_DIR="$(CURDIR)/$(FRONTEND)/dist" \
		exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT)

demo-lan: build ## Like demo, but reachable from other devices on your WiFi
	@test -x $(PY) || { echo "✗ Backend venv missing — run 'make setup' first."; exit 1; }
	@ip=$$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "<your-LAN-IP>"); \
		echo "→ Santé on your network: http://$$ip:$(PORT)  (login: admin / admin — Ctrl-C to stop)"; \
		cd $(BACKEND) && SANTE_STATIC_DIR="$(CURDIR)/$(FRONTEND)/dist" \
			exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

seed: ## Reset the dev DB and load demo data (admin/admin + sample sales)
	@test -x $(PY) || { echo "✗ Backend venv missing — run 'make setup' first."; exit 1; }
	cd $(BACKEND) && .venv/bin/python seed_demo.py

test: test-backend test-frontend ## Run backend (pytest) + frontend (vitest) tests

test-backend: ## Run backend tests (pytest)
	@test -x $(PY) || { echo "✗ Backend venv missing — run 'make setup' first."; exit 1; }
	cd $(BACKEND) && .venv/bin/python -m pytest -q

test-frontend: ## Run frontend tests (vitest)
	@test -d $(FRONTEND)/node_modules || { echo "✗ Frontend deps missing — run 'make setup' first."; exit 1; }
	cd $(FRONTEND) && npm test

clean: ## Remove venv, node_modules, and build output
	rm -rf $(VENV) $(FRONTEND)/node_modules $(FRONTEND)/dist
	@echo "✓ Cleaned. Run 'make setup' to reinstall."
