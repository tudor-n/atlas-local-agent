import { app, BrowserWindow, ipcMain, screen } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
let mainWindow;

// Manual flag to bypass Windows borderless window reporting bugs
let isHubFullscreen = false;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 180, 
    height: 220,
    transparent: true,
    frame: false,
    hasShadow: false,
    alwaysOnTop: true,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.on('set-mode', (event, mode) => {
  if (!mainWindow) return;

  if (mode === 'widget') {
    if (mainWindow.isFullScreen()) mainWindow.setFullScreen(false);
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    isHubFullscreen = false;
    
    setTimeout(() => {
      mainWindow.setResizable(false);
      mainWindow.setMinimumSize(180, 220);
      mainWindow.setSize(180, 220); 
      mainWindow.setAlwaysOnTop(true);
      event.sender.send('fullscreen-status', false);
    }, 150);
    
  } else {
    mainWindow.setResizable(true);
    mainWindow.setMinimumSize(380, 600);
    mainWindow.setAlwaysOnTop(false);
    
    if (mainWindow.isFullScreen()) mainWindow.setFullScreen(false);
    isHubFullscreen = false; 
    
    setTimeout(() => {
      mainWindow.setSize(400, 640);
      mainWindow.center();
      event.sender.send('fullscreen-status', false);
    }, 150);
  }
});

ipcMain.on('toggle-fullscreen', (event) => {
  if (!mainWindow) return;
  
  if (isHubFullscreen || mainWindow.isFullScreen() || mainWindow.isMaximized()) {
    mainWindow.setFullScreen(false);
    mainWindow.unmaximize();
    isHubFullscreen = false;
    
    setTimeout(() => {
      mainWindow.setSize(400, 640);
      mainWindow.center();
      event.sender.send('fullscreen-status', false);
    }, 150);
  } else {
    mainWindow.setFullScreen(true);
    isHubFullscreen = true;
    event.sender.send('fullscreen-status', true);
  }
});

ipcMain.on('minimize-app', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('close-app', () => app.quit());