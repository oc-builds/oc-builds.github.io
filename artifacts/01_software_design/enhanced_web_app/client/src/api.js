/*
 * api.js
 * Purpose: Thin fetch wrapper for all backend calls. Attaches the JWT as a Bearer
 *          token, sends/parses JSON, and converts non-2xx responses into thrown
 *          Errors carrying the server's {error} message.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

/**
 * Perform an API request against the backend.
 *
 * @param {string} path   - Endpoint path beginning with "/api" (Vite proxies it).
 * @param {object} options
 * @param {string} [options.method]  - HTTP method, defaults to "GET".
 * @param {object} [options.body]    - Optional JSON-serializable request body.
 * @param {string} [options.token]   - Optional JWT for the Authorization header.
 * @returns {Promise<any>} Parsed JSON response body.
 * @throws {Error} On any non-2xx response. The thrown Error has a numeric
 *                 `status` property so callers can detect 401 / 403 cases.
 */
export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = {};

  // Only send a JSON content type when there is actually a body to encode.
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  // Attach the bearer token when the caller is authenticated.
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Some endpoints (for example DELETE) may return an empty body. Guard the
  // JSON parse so an empty response does not crash the wrapper.
  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const message =
      (data && data.error) || `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}
