// Inventory CRUD routes for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24 (service-layer refactor 2026-06-20)
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: the HTTP boundary for inventory management. After the Milestone Two
// single-responsibility refactor these handlers only: parse/validate the
// request, enforce auth/role via middleware, delegate to inventoryService, and
// shape the response. All SQL and business rules (SKU uniqueness, existence
// checks) now live in server/services/inventoryService.js.
//
// WHY role checks live in middleware, not the client: the React UI hides the
// edit/delete buttons from non-admins, but that is only a convenience. The
// authoritative RBAC check is requireRole('admin') on the server below, because
// a client control can be bypassed (curl, devtools) while the server cannot.

import { Router } from 'express';
import { z } from 'zod';
import { requireAuth, requireRole } from '../middleware/auth.js';
import {
  listItems,
  createItem,
  updateItem,
  deleteItem,
} from '../services/inventoryService.js';

const router = Router();

// Validation schema for creating or updating an inventory item.
const itemSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  sku: z.string().min(1, 'SKU is required'),
  quantity: z.number().int('Quantity must be an integer').min(0, 'Quantity cannot be negative'),
  location: z.string().optional().nullable(),
});

// All inventory routes require a valid JWT.
router.use(requireAuth);

/**
 * GET /api/inventory
 * Returns every inventory item, including the username of the last editor.
 */
router.get('/', (req, res, next) => {
  try {
    return res.status(200).json(listItems());
  } catch (err) {
    return next(err);
  }
});

/**
 * POST /api/inventory
 * Body: { name, sku, quantity, location }
 * Creates a new inventory item. Available to admin and staff users.
 */
router.post('/', (req, res, next) => {
  try {
    const parsed = itemSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.issues[0].message });
    }

    const item = createItem(parsed.data, req.user.id);
    return res.status(201).json({ item });
  } catch (err) {
    return next(err);
  }
});

/**
 * PUT /api/inventory/:id
 * Body: { name, sku, quantity, location }
 * Updates an existing inventory item. Restricted to admin users.
 */
router.put('/:id', requireRole('admin'), (req, res, next) => {
  try {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'Invalid item id' });
    }

    const parsed = itemSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.issues[0].message });
    }

    const item = updateItem(id, parsed.data, req.user.id);
    return res.status(200).json({ item });
  } catch (err) {
    return next(err);
  }
});

/**
 * DELETE /api/inventory/:id
 * Removes an inventory item. Restricted to admin users.
 */
router.delete('/:id', requireRole('admin'), (req, res, next) => {
  try {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'Invalid item id' });
    }

    deleteItem(id);
    return res.status(200).json({ success: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
