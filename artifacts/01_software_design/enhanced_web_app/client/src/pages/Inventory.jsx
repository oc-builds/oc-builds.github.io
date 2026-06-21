/*
 * Inventory.jsx
 * Purpose: Inventory list screen. Fetches all items, renders them in a table with
 *          a client-side name/SKU search box, and offers Add, Edit, and Delete
 *          actions. Edit and Delete are only shown to admin users; staff users
 *          see a read-only table.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import { apiRequest } from '../api.js';

export default function Inventory() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const isAdmin = user && user.role === 'admin';

  /**
   * Centralized API error handling. A 401 means the session is no longer valid,
   * so the user is logged out and returned to the login screen.
   */
  const handleApiError = useCallback(
    (err) => {
      if (err.status === 401) {
        logout();
        navigate('/login');
        return;
      }
      setError(err.message);
    },
    [logout, navigate]
  );

  /** Load the full inventory list from the backend. */
  const loadItems = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiRequest('/api/inventory', { token });
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  }, [token, handleApiError]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  /** Delete an item after confirmation, then refresh the list. */
  async function handleDelete(item) {
    const confirmed = window.confirm(`Delete "${item.name}"? This cannot be undone.`);
    if (!confirmed) return;

    setError('');
    try {
      await apiRequest(`/api/inventory/${item.id}`, {
        method: 'DELETE',
        token,
      });
      await loadItems();
    } catch (err) {
      if (err.status === 403) {
        setError('Only administrators can delete inventory items.');
        return;
      }
      handleApiError(err);
    }
  }

  // Filter the table by name or SKU as the user types (case-insensitive).
  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return items;
    return items.filter((item) => {
      const name = (item.name || '').toLowerCase();
      const sku = (item.sku || '').toLowerCase();
      return name.includes(query) || sku.includes(query);
    });
  }, [items, search]);

  /** Format an ISO timestamp into a readable local date/time. */
  function formatDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  return (
    <div className="app-shell">
      <header className="app-bar">
        <h1 className="app-bar-title">CS360 Inventory Manager</h1>
        <div className="app-bar-actions">
          {user && (
            <span className="user-chip">
              {user.username} ({user.role})
            </span>
          )}
          <button
            type="button"
            className="btn btn-text"
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            Log out
          </button>
        </div>
      </header>

      <main className="content">
        <div className="toolbar">
          <input
            className="text-input search-input"
            type="search"
            placeholder="Search by name or SKU"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/items/new')}
          >
            Add Item
          </button>
        </div>

        {!isAdmin && (
          <p className="info-banner">
            You are signed in as staff. The inventory list is read-only;
            administrators can add, edit, and delete items.
          </p>
        )}

        {error && <p className="error-message">{error}</p>}

        {loading ? (
          <p className="muted-text">Loading inventory&hellip;</p>
        ) : filteredItems.length === 0 ? (
          <p className="muted-text">
            {items.length === 0
              ? 'No inventory items yet.'
              : 'No items match your search.'}
          </p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>SKU</th>
                  <th>Quantity</th>
                  <th>Location</th>
                  <th>Last Updated By</th>
                  {isAdmin && <th className="actions-col">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.sku}</td>
                    <td>{item.quantity}</td>
                    <td>{item.location}</td>
                    <td>
                      {item.updated_by_username || '-'}
                      <span className="cell-subtext">
                        {formatDate(item.updated_at)}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="actions-col">
                        <button
                          type="button"
                          className="btn btn-small btn-secondary"
                          onClick={() => navigate(`/items/${item.id}/edit`)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-small btn-danger"
                          onClick={() => handleDelete(item)}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
