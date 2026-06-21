// Authentication routes for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24 (service-layer refactor 2026-06-20)
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: the HTTP boundary for user registration and login. Following the
// single-responsibility refactor requested in Milestone Two feedback, these
// handlers do only three things: (1) validate the incoming request body with
// zod, (2) delegate to authService for all business logic, crypto, and data
// access, and (3) shape the HTTP response. No bcrypt, no jwt, and no db calls
// live here anymore, that logic moved to server/services/authService.js.

import { Router } from 'express';
import { z } from 'zod';
import { registerUser, loginUser } from '../services/authService.js';

const router = Router();

// Validation schema shared by register and login. Username must be at least
// 3 characters and password at least 6 characters.
const credentialsSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

/**
 * POST /api/auth/register
 * Body: { username, password }
 * Creates a new account. The first account ever created becomes "admin";
 * all later accounts default to "staff" (rule enforced in authService).
 */
router.post('/register', (req, res, next) => {
  try {
    const parsed = credentialsSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.issues[0].message });
    }

    const { token, user } = registerUser(parsed.data);
    return res.status(201).json({ token, user });
  } catch (err) {
    // ServiceError (e.g. 409 username taken) and any unexpected error both flow
    // to the global error handler, which maps err.status to the response.
    return next(err);
  }
});

/**
 * POST /api/auth/login
 * Body: { username, password }
 * Verifies credentials and returns a fresh JWT on success.
 */
router.post('/login', (req, res, next) => {
  try {
    const parsed = credentialsSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.issues[0].message });
    }

    const { token, user } = loginUser(parsed.data);
    return res.status(200).json({ token, user });
  } catch (err) {
    return next(err);
  }
});

export default router;
