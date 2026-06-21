/*
 * vite.config.js
 * Purpose: Vite build/dev configuration for the inventory client. Registers the
 *          React plugin and proxies "/api" requests to the backend on port 4000
 *          during development so the browser never makes a cross-origin call.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward any "/api/..." request from the dev server to the Express backend.
      // This keeps API calls same-origin in the browser and avoids CORS handling.
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
      },
    },
  },
});
