// Authentication and authorization middleware for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-05-24
// CS499 Enhancement One rebuild of the CS360 Android Inventory App.
//
// Purpose: provide reusable Express middleware that (1) verifies the JWT sent
// in the Authorization header and attaches the decoded user to the request,
// and (2) restricts a route to a specific user role.
//
// WHY authorization lives here and not in the client: the React UI hides admin
// actions from staff users, but that is only cosmetic, anyone can craft a raw
// HTTP request. requireAuth and requireRole are the authoritative gate: the
// server independently verifies the signed token and the user's role on every
// protected request, so a tampered or replayed client cannot escalate access.

import jwt from 'jsonwebtoken';

/**
 * requireAuth, verifies the bearer token on the request.
 *
 * Expects an "Authorization: Bearer <token>" header. On success it attaches
 * the decoded payload ({ id, username, role }) to req.user and calls next().
 * On failure it responds with HTTP 401 and a JSON error message.
 */
export function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';

  // The header must be present and formatted as "Bearer <token>".
  if (!header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or malformed Authorization header' });
  }

  const token = header.slice('Bearer '.length).trim();

  try {
    // jwt.verify throws if the token is invalid, expired, or tampered with.
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = { id: decoded.id, username: decoded.username, role: decoded.role };
    return next();
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

/**
 * requireRole, builds middleware that allows only a specific role.
 *
 * Must be used after requireAuth so that req.user is already populated.
 * Responds with HTTP 403 when the authenticated user lacks the role.
 *
 * @param {string} role - the role required to access the route (e.g. 'admin').
 */
export function requireRole(role) {
  return function roleGuard(req, res, next) {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: `Forbidden: ${role} role required` });
    }
    return next();
  };
}
