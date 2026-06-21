// Shared service-layer error type for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-06-20
// CS499 Capstone final-portfolio polish of Enhancement One.
//
// Purpose: give the service layer a single, HTTP-agnostic way to report an
// expected business-rule failure (a taken username, a duplicate SKU, a missing
// record, bad credentials, and so on).
//
// WHY this exists: Dr. Bolton's Milestone Two feedback asked for a real service
// layer that isolates business logic from the Express/HTTP routing layer. For
// that boundary to be clean, the services must NOT import Express or call
// res.status(...). Instead a service throws a ServiceError carrying a numeric
// `status`, and the route handler is the only place that translates that status
// into an HTTP response. The single global error handler in index.js performs
// that translation uniformly, so the routes stay thin and the services stay
// framework-free and unit-testable.

/**
 * ServiceError, an expected, client-facing failure raised by the service layer.
 *
 * The `status` field is the HTTP status the route/error-handler should emit.
 * Using a dedicated subclass lets the global error handler distinguish these
 * deliberate business-rule errors (which carry a safe message) from unexpected
 * programmer errors (which should surface as a generic 500).
 */
export class ServiceError extends Error {
  /**
   * @param {number} status - HTTP status code to surface (e.g. 409, 404, 401).
   * @param {string} message - safe, client-facing message.
   */
  constructor(status, message) {
    super(message);
    this.name = 'ServiceError';
    this.status = status;
  }
}
