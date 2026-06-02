const { contextBridge } = require("electron");

// Minimal bridge for now; expanded in later phases (print-to-PDF, file dialogs).
contextBridge.exposeInMainWorld("sante", {
  version: "0.0.1",
});
