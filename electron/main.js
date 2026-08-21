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
