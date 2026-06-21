/*
 * auth.jsx
 * Purpose: Authentication context for the inventory client. Stores the JWT and
 *          current user, and exposes login, register, and logout helpers.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 *
 * SECURITY NOTE: The token and user are held in React state IN MEMORY ONLY.
 * They are never written to localStorage or sessionStorage. This is a deliberate
 * security choice: a token kept only in memory cannot be read by any persistent
 * cross-site-scripting payload and is automatically discarded on page refresh,
 * at which point the user simply logs in again.
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { apiRequest } from './api.js';

const AuthContext = createContext(null);

/**
 * Provides authentication state and actions to the component tree.
 */
export function AuthProvider({ children }) {
  // In-memory only. Refreshing the page clears these by design.
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  /**
   * Send credentials to the given auth endpoint and store the result.
   * @param {string} endpoint - "/api/auth/login" or "/api/auth/register".
   */
  const authenticate = useCallback(async (endpoint, username, password) => {
    const data = await apiRequest(endpoint, {
      method: 'POST',
      body: { username, password },
    });
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const login = useCallback(
    (username, password) =>
      authenticate('/api/auth/login', username, password),
    [authenticate]
  );

  const register = useCallback(
    (username, password) =>
      authenticate('/api/auth/register', username, password),
    [authenticate]
  );

  /** Clear all authentication state. */
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = { token, user, login, register, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook for consuming authentication state and actions.
 * @returns {{token:string|null, user:object|null, login:Function,
 *            register:Function, logout:Function}}
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
