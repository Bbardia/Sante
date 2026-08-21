# Building the Windows Installer

The build produces **one file** — `Santé Setup x.y.z.exe` — a one-click NSIS
installer that bundles the FastAPI backend (as a PyInstaller exe) and the built
React SPA inside an Electron shell. The target PC needs **no Python, Node, or
npm**: the user just double-clicks the installer.

> **Why a Windows machine is involved:** PyInstaller cannot cross-compile, so the
> backend `.exe` can only be built on Windows. The recommended path below uses a
> cloud Windows machine (GitHub Actions), so you don't need one of your own.

---

## Recommended: build in the cloud with GitHub Actions

The workflow [`.github/workflows/build-windows.yml`](.github/workflows/build-windows.yml)
builds the whole installer on a Windows runner. Nothing to install locally.

### Trigger a build by pushing a version tag (primary path)

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow then:

1. Builds `sante-backend.exe` (PyInstaller), the SPA (Vite), and the installer
   (electron-builder), naming everything after the tag (`v0.1.0` → `0.1.0`).
2. Attaches `Santé Setup 0.1.0.exe` to a **GitHub Release** for that tag — a
   permanent download link.

Download the `.exe` from the repo's **Releases** page and copy it to any Windows PC.

### Or trigger manually

In the repo's **Actions** tab → **Build Windows Installer** → **Run workflow**.
The installer is uploaded as a downloadable **artifact** on that run (no Release).

> **Notes**
> - No secrets/tokens needed — the Release upload uses the built-in `GITHUB_TOKEN`.
> - The app is **unsigned**, so Windows SmartScreen shows "Unknown publisher" on
>   first run → **More info → Run anyway**.
> - For `workflow_dispatch` to appear and for tags to use it, the workflow file
>   must be on the **default branch** (`main`).

---

## Alternative: build locally on a Windows PC/VM

If you have a Windows machine with **Python 3.11+** and **Node.js 18+**, run the
one-command script from the repo root:

```cmd
build-windows.bat
```

It runs all three steps below and leaves the installer in `electron\release\`.

<details>
<summary>The three steps the script (and CI) run, if you want to run them by hand</summary>

```cmd
REM 1. Backend -> backend\dist\sante-backend.exe
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller sante-backend.spec
cd ..

REM 2. Frontend -> frontend\dist\
cd frontend
npm ci
npm run build
cd ..

REM 3. Installer -> electron\release\
cd electron
npm ci
npm run dist
```

</details>

The installer bundles:
- `resources\backend\sante-backend.exe` — the PyInstaller-packaged FastAPI server
- `resources\frontend\` — the built Vite/React SPA (served by the backend via `SANTE_STATIC_DIR`)

---

## How it works at runtime

1. Electron spawns `sante-backend.exe` with `SANTE_STATIC_DIR` (the bundled SPA)
   and `SANTE_DATA_DIR` (a writable per-user folder).
2. The FastAPI backend serves the SPA from `SANTE_STATIC_DIR` (mounted last, so
   API routes take priority).
3. Electron loads `http://127.0.0.1:8756` — the UI is same-origin with the API,
   no CORS needed.

### Where the database lives

At runtime the backend stores `database.db` in `SANTE_DATA_DIR`, which Electron
sets to its per-user data folder — **`%APPDATA%\Santé\database.db`** on Windows.
This matters because the install directory under `Program Files` is read-only;
keeping data in `%APPDATA%` also means **business data survives app upgrades and
uninstalls**. (With no `SANTE_DATA_DIR` set, e.g. in local dev, the backend falls
back to `backend\database.db`.)

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Backend failed to start" screen | `sante-backend.exe` missing or crashed on launch. To see backend logs, temporarily set `console=True` in `backend/sante-backend.spec`, rebuild, and watch the console. |
| Blank/white screen | Frontend `dist` not copied correctly into `resources\frontend\`. |
| API 500 errors | `%APPDATA%\Santé\` not writable, or a corrupt `database.db` there. |
| CI build fails in the PyInstaller step | A hidden import is missing — add it to `hiddenimports` in `backend/sante-backend.spec` and re-run. |
| "Unknown publisher" SmartScreen warning | Expected (app is unsigned) → **More info → Run anyway**. |
