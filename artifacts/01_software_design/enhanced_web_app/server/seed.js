// Database seed script for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: populate the database with demo data for development and grading.
// It creates an admin and a staff account plus a set of realistic synthetic
// inventory items. The script is idempotent, running it repeatedly will not
// create duplicates.

import 'dotenv/config';
import bcrypt from 'bcryptjs';
import db from './db.js';

const SALT_ROUNDS = 10;

/**
 * Inserts a user account if it does not already exist.
 * @param {string} username
 * @param {string} password - plaintext password, hashed before storage
 * @param {string} role - 'admin' or 'staff'
 * @returns {number} the id of the existing or newly created user
 */
function ensureUser(username, password, role) {
  const existing = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
  if (existing) {
    console.log(`User "${username}" already exists, skipping.`);
    return existing.id;
  }
  const hash = bcrypt.hashSync(password, SALT_ROUNDS);
  const result = db
    .prepare('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)')
    .run(username, hash, role);
  console.log(`Created ${role} user "${username}".`);
  return result.lastInsertRowid;
}

/**
 * Inserts an inventory item if no item with the same SKU already exists.
 * @param {{name:string, sku:string, quantity:number, location:string}} item
 * @param {number} updatedBy - id of the user credited with the change
 */
function ensureItem(item, updatedBy) {
  const existing = db.prepare('SELECT id FROM inventory_items WHERE sku = ?').get(item.sku);
  if (existing) {
    return;
  }
  db.prepare(
    `INSERT INTO inventory_items (name, sku, quantity, location, updated_at, updated_by)
     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)`
  ).run(item.name, item.sku, item.quantity, item.location, updatedBy);
}

// Create the demo accounts. Credentials are intentionally simple for grading.
const adminId = ensureUser('admin', 'admin123', 'admin');
ensureUser('staff', 'staff123', 'staff');

console.log('\n--- Demo Credentials ---');
console.log('Admin  →  username: admin   password: admin123');
console.log('Staff  →  username: staff   password: staff123');
console.log('------------------------\n');

// Realistic synthetic inventory covering an electrical/hardware warehouse.
const seedItems = [
  { name: '12 AWG THHN Copper Wire (500 ft)', sku: 'WIRE-12THHN-500', quantity: 42, location: 'Aisle 1 - Bin 04' },
  { name: '14 AWG Romex NM-B Cable (250 ft)', sku: 'WIRE-14NMB-250', quantity: 30, location: 'Aisle 1 - Bin 07' },
  { name: 'Single-Pole Light Switch (White)', sku: 'SW-SPST-WHT', quantity: 180, location: 'Aisle 2 - Bin 11' },
  { name: 'Duplex Receptacle 15A (Ivory)', sku: 'RCPT-15A-IVY', quantity: 220, location: 'Aisle 2 - Bin 14' },
  { name: '20A GFCI Outlet (White)', sku: 'RCPT-GFCI-20A', quantity: 65, location: 'Aisle 2 - Bin 18' },
  { name: '1/2 in. EMT Conduit (10 ft)', sku: 'CON-EMT-050', quantity: 96, location: 'Aisle 3 - Bin 02' },
  { name: '3/4 in. PVC Conduit (10 ft)', sku: 'CON-PVC-075', quantity: 74, location: 'Aisle 3 - Bin 05' },
  { name: 'Single-Gang Old-Work Box', sku: 'BOX-1G-OW', quantity: 310, location: 'Aisle 3 - Bin 12' },
  { name: '20A Single-Pole Circuit Breaker', sku: 'BRK-20A-1P', quantity: 58, location: 'Aisle 4 - Bin 03' },
  { name: '40A Double-Pole Circuit Breaker', sku: 'BRK-40A-2P', quantity: 26, location: 'Aisle 4 - Bin 06' },
  { name: 'Wire Connectors - Yellow (100 pack)', sku: 'CONN-WN-YEL-100', quantity: 140, location: 'Aisle 5 - Bin 09' },
  { name: 'LED Recessed Downlight 6 in.', sku: 'LGT-LED-6IN', quantity: 88, location: 'Aisle 6 - Bin 01' },
  { name: '4 ft LED Shop Light Fixture', sku: 'LGT-LED-4FT', quantity: 34, location: 'Aisle 6 - Bin 04' },
  { name: 'Electrical Tape - Black (3/4 in.)', sku: 'TAPE-ELEC-BLK', quantity: 260, location: 'Aisle 7 - Bin 15' },
  { name: 'Voltage Tester Pen (Non-Contact)', sku: 'TOOL-VTEST-NC', quantity: 47, location: 'Aisle 8 - Bin 21' },
];

let inserted = 0;
for (const item of seedItems) {
  const before = db.prepare('SELECT COUNT(*) AS c FROM inventory_items').get().c;
  ensureItem(item, adminId);
  const after = db.prepare('SELECT COUNT(*) AS c FROM inventory_items').get().c;
  if (after > before) inserted += 1;
}

console.log(`Seed complete. Inserted ${inserted} new inventory item(s).`);
