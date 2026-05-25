const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const rootDir = path.resolve(__dirname, "..");
const pythonBin = process.env.TWEETER_PYTHON || "python3";
const iconPath = path.join(__dirname, "assets", process.platform === "darwin" ? "icon.icns" : process.platform === "win32" ? "icon.ico" : "icon.png");
let oauthProcess = null;
let oauthLog = [];

function runtimeEnv() {
  return {
    ...process.env,
    TWEETER_DATA_DIR: app.isPackaged ? app.getPath("userData") : rootDir
  };
}

function runtimeCwd() {
  return app.isPackaged ? process.resourcesPath : rootDir;
}

function pythonTarget(scriptName) {
  const binaryName = process.platform === "win32"
    ? `${path.basename(scriptName, ".py")}.exe`
    : path.basename(scriptName, ".py");
  const packagedBinary = path.join(process.resourcesPath, "bin", binaryName);
  if (app.isPackaged) {
    return { command: packagedBinary, args: [] };
  }
  return { command: pythonBin, args: [path.join(rootDir, scriptName)] };
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1120,
    minHeight: 720,
    title: "Tweeter Studio",
    icon: iconPath,
    backgroundColor: "#f5f7fb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile(path.join(__dirname, "renderer", "index.html"));
}

function runPython(command, payload = {}) {
  return new Promise((resolve, reject) => {
    const target = pythonTarget("ui_api.py");
    const child = spawn(
      target.command,
      [...target.args, command, JSON.stringify(payload)],
      {
        cwd: runtimeCwd(),
        env: runtimeEnv(),
        stdio: ["ignore", "pipe", "pipe"]
      }
    );

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", () => {
      const raw = stdout.trim().split(/\r?\n/).filter(Boolean).at(-1);
      if (!raw) {
        reject(new Error(stderr || "Python bridge returned no output."));
        return;
      }
      try {
        const parsed = JSON.parse(raw);
        if (!parsed.ok) {
          reject(new Error(parsed.error || stderr || "Python bridge failed."));
          return;
        }
        resolve(parsed.data);
      } catch (error) {
        reject(new Error(`Could not parse Python response: ${error.message}\n${stdout}\n${stderr}`));
      }
    });
  });
}

function runPythonStream(sender, command, payload = {}) {
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const send = (event) => sender.send("api:stream-event", id, event);

  setImmediate(() => {
    const target = pythonTarget("ui_live.py");
    const child = spawn(
      target.command,
      [...target.args, command, JSON.stringify(payload)],
      {
        cwd: runtimeCwd(),
        env: runtimeEnv(),
        stdio: ["ignore", "pipe", "pipe"]
      }
    );

    let stdoutBuffer = "";
    const consume = (chunk) => {
      stdoutBuffer += chunk.toString();
      while (stdoutBuffer.includes("\n")) {
        const [line, ...rest] = stdoutBuffer.split("\n");
        stdoutBuffer = rest.join("\n");
        if (!line.trim()) continue;
        try {
          send(JSON.parse(line));
        } catch {
          send({ type: "line", line });
        }
      }
    };

    child.stdout.on("data", consume);
    child.stderr.on("data", (chunk) => {
      send({ type: "line", stream: "stderr", line: chunk.toString() });
    });
    child.on("error", (error) => {
      send({ type: "error", error: error.message });
    });
    child.on("close", (code, signal) => {
      if (stdoutBuffer.trim()) {
        try {
          send(JSON.parse(stdoutBuffer.trim()));
        } catch {
          send({ type: "line", line: stdoutBuffer.trim() });
        }
      }
      send({ type: "closed", code, signal });
    });
  });

  return id;
}

function startOauthProxy() {
  if (oauthProcess && !oauthProcess.killed) {
    return { running: true, log: oauthLog.slice(-80) };
  }
  oauthLog = ["npx openai-oauth başlatılıyor..."];
  oauthProcess = spawn("npx", ["openai-oauth"], {
    cwd: runtimeCwd(),
    env: runtimeEnv(),
    shell: process.platform === "win32",
    stdio: ["ignore", "pipe", "pipe"]
  });
  const append = (chunk) => {
    oauthLog.push(chunk.toString());
    oauthLog = oauthLog.slice(-120);
  };
  oauthProcess.stdout.on("data", append);
  oauthProcess.stderr.on("data", append);
  oauthProcess.on("error", (error) => append(`OAuth proxy error: ${error.message}`));
  oauthProcess.on("close", (code, signal) => {
    append(`OAuth proxy kapandı. code=${code ?? "-"} signal=${signal ?? "-"}`);
    oauthProcess = null;
  });
  return { running: true, log: oauthLog.slice(-80) };
}

function stopOauthProxy() {
  if (oauthProcess && !oauthProcess.killed) {
    oauthProcess.kill();
  }
  oauthProcess = null;
  return { running: false, log: oauthLog.slice(-80) };
}

ipcMain.handle("api:call", async (_event, command, payload) => {
  return runPython(command, payload);
});

ipcMain.handle("api:stream", async (event, command, payload) => {
  return runPythonStream(event.sender, command, payload);
});

ipcMain.handle("ai:start-oauth", async () => startOauthProxy());

ipcMain.handle("ai:stop-oauth", async () => stopOauthProxy());

ipcMain.handle("ai:oauth-status", async () => ({
  running: Boolean(oauthProcess && !oauthProcess.killed),
  log: oauthLog.slice(-80)
}));

ipcMain.handle("dialog:images", async () => {
  const result = await dialog.showOpenDialog({
    title: "Görsel seç",
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Images", extensions: ["png", "jpg", "jpeg", "gif", "webp"] }
    ]
  });
  return result.canceled ? [] : result.filePaths.slice(0, 4);
});

app.whenReady().then(() => {
  if (process.platform === "darwin" && app.dock) {
    app.dock.setIcon(path.join(__dirname, "assets", "icon.png"));
  }
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
