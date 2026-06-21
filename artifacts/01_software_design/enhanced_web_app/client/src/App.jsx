/*
 * App.jsx
 * Purpose: Root component and route table for the inventory client. Defines the
 *          login, inventory, and item-form routes and a protected-route wrapper
 *          that redirects unauthenticated users to the login screen.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import Login from './pages/Login.jsx';
import Inventory from './pages/Inventory.jsx';
import ItemForm from './pages/ItemForm.jsx';

/**
 * Wraps a protected route. If there is no token in memory the user is sent to
 * the login screen instead of seeing the requested page.
 */
function RequireAuth({ children }) {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Inventory />
          </RequireAuth>
        }
      />
      <Route
        path="/items/new"
        element={
          <RequireAuth>
            <ItemForm />
          </RequireAuth>
        }
      />
      <Route
        path="/items/:id/edit"
        element={
          <RequireAuth>
            <ItemForm />
          </RequireAuth>
        }
      />
      {/* Any unknown path falls back to the inventory route. */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
