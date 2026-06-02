const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");
const path = require("path");

const BACKEND_PORT = 8756;
const DEV_URL = "http://localhost:5173";

let backendProcess = null;

function startBackend() {
  // Dev: run uvicorn from the backend venv (macOS/Linux path; Windows handled in the packaging phase).
  const pythonBin = path.join(__dirname, "..", "backend", ".venv", "bin", "python");
  if (!fs.existsSync(pythonBin)) {
    console.error(`[backend] Python not found at ${pythonBin} — did you create backend/.venv?`);
    return; // backendProcess stays null; waitForBackend will time out and show the error page
  }
  backendProcess = spawn(
    pythonBin,
    ["-m", "uvicorn", "app.main:app", "--port", String(BACKEND_PORT)],
    { cwd: path.join(__dirname, "..", "backend"), stdio: "inherit" },
  );
  backendProcess.on("error", (err) => {
    console.error("Failed to start backend:", err);
  });
}

// Version-agnostic health poll using Node's built-in http (works on any Electron/Node version;
// global fetch only exists in Electron >= 22 / Node >= 18).
function waitForBackend() {
  return new Promise((resolve) => {
    let attempts = 0;
    function probe() {
      const req = http.get(`http://localhost:${BACKEND_PORT}/health`, (res) => {
        res.resume();
        resolve(res.statusCode >= 200 && res.statusCode < 300);
      });
      req.on("error", () => {
        if (++attempts < 50) setTimeout(probe, 200);
        else resolve(false);
      });
      req.setTimeout(500, () => req.destroy());
    }
    probe();
  });
}

function killBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
    backendProcess = null;
  }
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
  // Intentional: quit on window close on all platforms (single-window POS app).
  killBackend();
  app.quit();
});

app.on("before-quit", killBackend);
process.on("SIGTERM", () => { killBackend(); process.exit(0); });
process.on("SIGINT", () => { killBackend(); process.exit(0); });
