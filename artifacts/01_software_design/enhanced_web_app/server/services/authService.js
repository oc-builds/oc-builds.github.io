// Authentication service for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-06-20
// CS499 Capstone final-portfolio polish of Enhancement One.
//
// Purpose: own ALL authentication business rules and data access for user
// accounts, password hashing, JWT signing, the first-user-becomes-admin rule,
// duplicate-username handling, and credential verification. The Express route
// layer (routes/auth.js) calls these functions and never touches the database
// or the crypto libraries directly.
//
// ENCAPSULATION (B2): JavaScript modules have no `private` keyword, so this file
// documents its boundary by convention. The PUBLIC service API is exactly the
// two exported functions, registerUser() and loginUser(). Everything else
// (signToken, the SALT_ROUNDS constant, the prepared statements) is module-
// internal: it is NOT exported, so no other module can reach it. That closure
// over module scope is the encapsulation mechanism here.

import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import db from '../db.js';
import { ServiceError } from './serviceError.js';

// --- Module-internal state (not exported = effectively private) ---------------

// Number of bcrypt salt rounds. WHY 10: bcrypt is intentionally slow, and 10
// rounds (~2^10 iterations) is the widely accepted balance between resistance
// to offline brute-force attacks and acceptable login latency on commodity
// hardware. Storing the salt rounds in the hash also lets the cost be raised
// later without invalidating existing hashes.
const SALT_ROUNDS = 10;

// Prepared statements are created once at module load. WHY parameterized: the
// `?` placeholders make these statements immune to SQL injection, user input
// is always bound as data, never concatenated into the SQL text.
const findByUsernameStmt = db.prepare(
  'SELECT id, username, password_hash, role FROM users WHERE username = ?'
);
const countUsersStmt = db.prepare('SELECT COUNT(*) AS count FROM users');
const insertUserStmt = db.prepare(
  'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)'
);

/**
 * signToken, internal helper that mints a signed JWT for a user record.
 *
 * WHY a JWT: it lets the API stay stateless, the server does not keep a session
 * table; every request carries its own verifiable proof of identity and role.
 * The role is embedded in the token so the authorization middleware can enforce
 * RBAC without an extra database lookup on every request.
 *
 * @param {{id:number, username:string, role:string}} user
 * @returns {string} signed token (expires in 8h)
 */
function signToken(user) {
  return jwt.sign(
    { id: user.id, username: user.username, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: '8h' }
  );
}

// --- Public service API -------------------------------------------------------

/**
 * registerUser, create a new account and return a signed session token.
 *
 * Business rules enforced here (not in the route):
 *   - usernames must be unique (409 on conflict);
 *   - the very first account ever created is promoted to "admin", every later
 *     account defaults to "staff", this bootstraps the system with one admin
 *     without hard-coding credentials;
 *   - the plaintext password is hashed with bcrypt and never stored.
 *
 * @param {{username:string, password:string}} credentials - already validated.
 * @returns {{token:string, user:{id:number, username:string, role:string}}}
 * @throws {ServiceError} 409 if the username is already taken.
 */
export function registerUser({ username, password }) {
  // Reject duplicate usernames before attempting an insert.
  const existing = findByUsernameStmt.get(username);
  if (existing) {
    throw new ServiceError(409, 'Username already taken');
  }

  // The very first user to register is promoted to the admin role.
  const userCount = countUsersStmt.get().count;
  const role = userCount === 0 ? 'admin' : 'staff';

  // Hash the password, the plaintext password is never stored.
  const passwordHash = bcrypt.hashSync(password, SALT_ROUNDS);

  const result = insertUserStmt.run(username, passwordHash, role);
  const user = { id: result.lastInsertRowid, username, role };

  return { token: signToken(user), user };
}

/**
 * loginUser, verify credentials and return a fresh session token.
 *
 * WHY a single generic error: the same "Invalid username or password" message
 * is returned whether the username is unknown or the password is wrong, so an
 * attacker cannot use the response to enumerate which usernames exist.
 *
 * @param {{username:string, password:string}} credentials - already validated.
 * @returns {{token:string, user:{id:number, username:string, role:string}}}
 * @throws {ServiceError} 401 if the credentials are invalid.
 */
export function loginUser({ username, password }) {
  const account = findByUsernameStmt.get(username);

  if (!account || !bcrypt.compareSync(password, account.password_hash)) {
    throw new ServiceError(401, 'Invalid username or password');
  }

  const user = { id: account.id, username: account.username, role: account.role };
  return { token: signToken(user), user };
}
