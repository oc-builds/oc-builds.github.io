// Application entry point for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: configure and start the Express application. It wires up CORS for
// the React frontend, JSON body parsing, the authentication and inventory
// routers, and a global JSON error handler. The server fails fast with a
// clear message if the JWT secret is not configured.

import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import authRouter from './routes/auth.js';
import inventoryRouter from './routes/inventory.js';

// Fail fast: the JWT secret is mandatory for signing and verifying tokens.
if (!process.env.JWT_SECRET) {
  console.error(
    'FATAL: JWT_SECRET is not set. Copy .env.example to .env and set a value before starting.'
  );
  process.exit(1);
}

const app = express();
const PORT = process.env.PORT || 4000;

// Allow the Vite-based React frontend (default dev port 5173) to call the API.
app.use(cors({ origin: 'http://localhost:5173' }));

// Parse incoming JSON request bodies.
app.use(express.json());

// Simple health-check endpoint for quick verification.
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Mount the feature routers.
app.use('/api/auth', authRouter);
app.use('/api/inventory', inventoryRouter);

// Catch-all for unknown routes, always responds with JSON.
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Global error handler. Any error passed to next(err) is converted into a
// consistent JSON response so the frontend never receives an HTML error page.
//
// WHY the status split: the service layer throws ServiceError with a 4xx status
// for expected business-rule failures (duplicate SKU, bad credentials, missing
// record). Those carry a safe, client-facing message and are NOT logged as
// server faults. Anything without a 4xx status is an unexpected programmer error
// it is logged for diagnosis and reported to the client as a generic 500 so
// internal details (stack traces, SQL text) are never leaked.
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  const status = err.status || 500;
  if (status >= 500) {
    console.error('Unhandled error:', err);
    return res.status(status).json({ error: 'Internal server error' });
  }
  return res.status(status).json({ error: err.message });
});

app.listen(PORT, () => {
  // Intentional startup banner, useful operational output, not debugging noise.
  // eslint-disable-next-line no-console
  console.log(`CS360 Inventory Server listening on http://localhost:${PORT}`);
});
