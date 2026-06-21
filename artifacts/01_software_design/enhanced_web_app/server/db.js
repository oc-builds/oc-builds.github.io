// Database bootstrap module for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: open (or create on first run) the embedded SQLite database file,
// apply the schema if the tables are missing, and export a shared database
// handle for the rest of the application to use. No separate database server
// is required, better-sqlite3 stores everything in a local file.

import Database from 'better-sqlite3';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Resolve paths relative to this file so the server works from any directory.
const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, 'inventory.db');
const SCHEMA_PATH = join(__dirname, 'schema.sql');

// Open the database file. better-sqlite3 creates the file if it does not exist.
const db = new Database(DB_PATH);

// Enforce foreign key constraints (off by default in SQLite).
db.pragma('foreign_keys = ON');

// Apply the schema only when the core tables are missing. The schema uses
// "CREATE TABLE IF NOT EXISTS", so re-running it is safe and idempotent.
const usersTableExists = db
  .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'")
  .get();

if (!usersTableExists) {
  const schema = readFileSync(SCHEMA_PATH, 'utf8');
  db.exec(schema);
  // Intentional one-time startup message confirming first-run initialization.
  // eslint-disable-next-line no-console
  console.log('Database schema initialized.');
}

export default db;
