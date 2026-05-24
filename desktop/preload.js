const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tweeterAPI", {
  call(command, payload) {
    return ipcRenderer.invoke("api:call", command, payload || {});
  },
  stream(command, payload) {
    return ipcRenderer.invoke("api:stream", command, payload || {});
  },
  onStreamEvent(callback) {
    const listener = (_event, id, data) => callback(id, data);
    ipcRenderer.on("api:stream-event", listener);
    return () => ipcRenderer.removeListener("api:stream-event", listener);
  },
  chooseImages() {
    return ipcRenderer.invoke("dialog:images");
  },
  startOauthProxy() {
    return ipcRenderer.invoke("ai:start-oauth");
  },
  stopOauthProxy() {
    return ipcRenderer.invoke("ai:stop-oauth");
  },
  oauthStatus() {
    return ipcRenderer.invoke("ai:oauth-status");
  }
});
