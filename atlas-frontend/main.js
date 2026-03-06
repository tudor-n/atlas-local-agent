import { app, BrowserWindow, ipcMain, screen } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 600,
    transparent: true, // Stark Industries transparent HUD
    frame: false,      // No Windows borders or close buttons
    hasShadow: false,
    alwaysOnTop: true, // Keep the orb above other windows
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  // Load the Vite dev server
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

// --- DYNAMIC RESIZING LOGIC ---
ipcMain.on('set-mode', (event, mode) => {
  if (!mainWindow) return;

  if (mode === 'widget') {
    // 1. Force state reset
    if (mainWindow.isFullScreen()) mainWindow.setFullScreen(false);
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    
    // 2. Delayed shrink to avoid "Ghost Window" bug
    setTimeout(() => {
      mainWindow.setResizable(false);
      mainWindow.setMinimumSize(150, 180);
      mainWindow.setSize(150, 180); 
      mainWindow.setAlwaysOnTop(true);
    }, 150);
  } else {
    // 3. Hub Mode: Unlock everything
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    mainWindow.setResizable(true);
    mainWindow.setMinimumSize(800, 600);
    mainWindow.setAlwaysOnTop(false);
    mainWindow.setSize(Math.floor(width * 0.9), Math.floor(height * 0.9));
    mainWindow.center();
  }
});

ipcMain.on('toggle-fullscreen', (event) => {
  if (!mainWindow) return;
  const isFS = mainWindow.isFullScreen();
  mainWindow.setFullScreen(!isFS);
  event.sender.send('fullscreen-status', !isFS);
});

ipcMain.on('close-app', () => app.quit());