@echo off
REM ============================================================================
REM  Santé - one-command Windows installer build (local fallback to CI).
REM
REM  Run this on a Windows PC/VM that has Python 3.11+ and Node.js 18+ installed.
REM  It produces electron\release\Santé Setup x.y.z.exe - a single one-click
REM  installer. The primary build path is GitHub Actions (push a v* tag); use
REM  this only when you want to build locally.
REM
REM  Usage (from the repo root):  build-windows.bat
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo [1/3] Building backend executable (PyInstaller)...
cd backend || exit /b 1
if not exist .venv (
    python -m venv .venv || exit /b 1
)
call .venv\Scripts\activate || exit /b 1
python -m pip install --upgrade pip || exit /b 1
pip install -r requirements.txt pyinstaller || exit /b 1
pyinstaller sante-backend.spec || exit /b 1
call .venv\Scripts\deactivate
cd ..

echo.
echo [2/3] Building frontend SPA...
cd frontend || exit /b 1
call npm ci || exit /b 1
call npm run build || exit /b 1
cd ..

echo.
echo [3/3] Building Windows installer (electron-builder)...
cd electron || exit /b 1
call npm ci || exit /b 1
call npm run dist || exit /b 1
cd ..

echo.
echo Done. Installer is in: electron\release\
dir /b electron\release\*.exe
endlocal
