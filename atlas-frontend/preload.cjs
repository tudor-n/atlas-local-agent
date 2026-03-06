const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  setMode: (mode) => ipcRenderer.send('set-mode', mode),
  toggleFullScreen: () => ipcRenderer.send('toggle-fullscreen'),
  closeApp: () => ipcRenderer.send('close-app'),
  onMaximizedStatus: (callback) => ipcRenderer.on('fullscreen-status', (_event, value) => callback(value)),
});