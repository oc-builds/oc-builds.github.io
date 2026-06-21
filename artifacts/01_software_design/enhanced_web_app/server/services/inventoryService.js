// Inventory service for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-06-20
// CS499 Capstone final-portfolio polish of Enhancement One.
//
// Purpose: own ALL inventory business rules and SQLite access, listing,
// creating, updating, and deleting items, plus the SKU-uniqueness and
// record-existence checks. The Express route layer (routes/inventory.js) calls
// these functions and never issues SQL itself.
//
// ENCAPSULATION (B2): the PUBLIC service API is the four exported functions
// (listItems, createItem, updateItem, deleteItem). The prepared statements and
// the SELECT_ITEM SQL fragment below are module-internal, not exported, so the
// rest of the app cannot bypass the service to reach the database. Closure over
// module scope is the privacy mechanism, since JS has no `private` keyword here.

import db from '../db.js';
import { ServiceError } from './serviceError.js';

// --- Module-internal data access (not exported = effectively private) ---------

// SQL fragment that returns an item joined with the username of the last editor.
// Reused by every read so all responses share an identical shape.
const SELECT_ITEM = `
  SELECT i.id, i.name, i.sku, i.quantity, i.location, i.updated_at,
         u.username AS updated_by_username
  FROM inventory_items i
  LEFT JOIN users u ON u.id = i.updated_by
`;

// Prepared statements built once at module load. WHY parameterized: every `?`
// binds user input as data, never as SQL text, which prevents SQL injection.
const listStmt = db.prepare(`${SELECT_ITEM} ORDER BY i.name COLLATE NOCASE`);
const getByIdStmt = db.prepare(`${SELECT_ITEM} WHERE i.id = ?`);
const findIdBySkuStmt = db.prepare('SELECT id FROM inventory_items WHERE sku = ?');
const findIdBySkuExcludingStmt = db.prepare(
  'SELECT id FROM inventory_items WHERE sku = ? AND id != ?'
);
const findIdByIdStmt = db.prepare('SELECT id FROM inventory_items WHERE id = ?');
const insertStmt = db.prepare(
  `INSERT INTO inventory_items (name, sku, quantity, location, updated_at, updated_by)
   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)`
);
const updateStmt = db.prepare(
  `UPDATE inventory_items
   SET name = ?, sku = ?, quantity = ?, location = ?,
       updated_at = CURRENT_TIMESTAMP, updated_by = ?
   WHERE id = ?`
);
const deleteStmt = db.prepare('DELETE FROM inventory_items WHERE id = ?');

// --- Public service API -------------------------------------------------------

/**
 * listItems, return every inventory item with its last-editor username.
 * @returns {Array<object>} items ordered by name (case-insensitive).
 */
export function listItems() {
  return listStmt.all();
}

/**
 * createItem, insert a new inventory item.
 *
 * Business rule enforced here: SKUs must be unique across all items.
 *
 * @param {{name:string, sku:string, quantity:number, location:?string}} data
 *        - request fields, already validated by the route.
 * @param {number} userId - id of the user credited as the last editor.
 * @returns {object} the created item in canonical SELECT_ITEM shape.
 * @throws {ServiceError} 409 if the SKU already exists.
 */
export function createItem({ name, sku, quantity, location }, userId) {
  if (findIdBySkuStmt.get(sku)) {
    throw new ServiceError(409, 'An item with that SKU already exists');
  }

  const result = insertStmt.run(name, sku, quantity, location ?? null, userId);
  return getByIdStmt.get(result.lastInsertRowid);
}

/**
 * updateItem, modify an existing inventory item.
 *
 * Business rules enforced here: the item must exist (404), and the new SKU must
 * not collide with a DIFFERENT item (409).
 *
 * @param {number} id - id of the item to update.
 * @param {{name:string, sku:string, quantity:number, location:?string}} data
 *        - request fields, already validated by the route.
 * @param {number} userId - id of the user credited as the last editor.
 * @returns {object} the updated item in canonical SELECT_ITEM shape.
 * @throws {ServiceError} 404 if the item does not exist, 409 on SKU clash.
 */
export function updateItem(id, { name, sku, quantity, location }, userId) {
  if (!findIdByIdStmt.get(id)) {
    throw new ServiceError(404, 'Inventory item not found');
  }

  if (findIdBySkuExcludingStmt.get(sku, id)) {
    throw new ServiceError(409, 'An item with that SKU already exists');
  }

  updateStmt.run(name, sku, quantity, location ?? null, userId, id);
  return getByIdStmt.get(id);
}

/**
 * deleteItem, remove an inventory item by id.
 *
 * @param {number} id - id of the item to delete.
 * @returns {void}
 * @throws {ServiceError} 404 if no item with that id exists.
 */
export function deleteItem(id) {
  const result = deleteStmt.run(id);
  if (result.changes === 0) {
    throw new ServiceError(404, 'Inventory item not found');
  }
}
