/*
 * Login.jsx
 * Purpose: Login screen for the inventory client. Provides username and password
 *          fields plus Login and Register buttons, mirroring the original Android
 *          app. Buttons stay disabled until both fields contain text, and server
 *          error messages are shown inline.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // The original Android app disabled both buttons until both fields had text.
  const fieldsFilled = username.trim() !== '' && password.trim() !== '';

  /**
   * Run a login or register action, then route to the inventory list on success.
   * @param {Function} action - Either the login or register function.
   */
  async function submit(action) {
    setError('');
    setBusy(true);
    try {
      await action(username.trim(), password);
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form
        className="card auth-card"
        onSubmit={(e) => {
          e.preventDefault();
          if (fieldsFilled && !busy) submit(login);
        }}
      >
        <h1 className="auth-title">CS360 Inventory Manager</h1>
        <p className="auth-subtitle">Sign in to continue</p>

        <label className="field-label" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          className="text-input"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <label className="field-label" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          className="text-input"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <p className="error-message">{error}</p>}

        <div className="button-row">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!fieldsFilled || busy}
          >
            Login
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!fieldsFilled || busy}
            onClick={() => submit(register)}
          >
            Register
          </button>
        </div>
      </form>
    </div>
  );
}
