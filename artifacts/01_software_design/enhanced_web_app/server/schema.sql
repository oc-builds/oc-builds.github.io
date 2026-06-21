-- Database schema for the CS360 Inventory Server.
-- Author: Sanjay Chauhan
-- Date: 2026-05-24
-- CS499 Enhancement One rebuild of the CS360 Android Inventory App.
--
-- This schema is executed automatically on first run (see db.js) to create
-- the SQLite tables backing the inventory management web application.

-- Application user accounts. The first account ever created is promoted to
-- the "admin" role; all later accounts default to "staff".
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'staff',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Inventory items tracked by the application. Each item records who last
-- updated it so the API can surface an "updated_by_username" value.
CREATE TABLE IF NOT EXISTS inventory_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    sku        TEXT UNIQUE NOT NULL,
    quantity   INTEGER NOT NULL,
    location   TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id)
);
