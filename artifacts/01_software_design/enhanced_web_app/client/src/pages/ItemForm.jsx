/*
 * ItemForm.jsx
 * Purpose: Combined create/edit form for inventory items. When a route :id is
 *          present the existing item is fetched and pre-filled and the submit
 *          performs a PUT; otherwise the submit performs a POST. Includes basic
 *          client-side validation.
 * Author:  Sanjay Chauhan
 * Date:    2026-05-24
 * Context: CS499 Enhancement One rebuild of the CS360 Android Inventory App.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import { apiRequest } from '../api.js';

export default function ItemForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: '',
    sku: '',
    quantity: '',
    location: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(isEdit);
  const [busy, setBusy] = useState(false);

  /** Shared API error handling; a 401 sends the user back to the login screen. */
  const handleApiError = useCallback(
    (err) => {
      if (err.status === 401) {
        logout();
        navigate('/login');
        return true;
      }
      return false;
    },
    [logout, navigate]
  );

  // When editing, load the existing item and pre-fill the form fields.
  useEffect(() => {
    if (!isEdit) return;

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        // The contract has no GET-by-id endpoint, so fetch the list and select.
        const data = await apiRequest('/api/inventory', { token });
        const found = Array.isArray(data)
          ? data.find((item) => String(item.id) === String(id))
          : null;
        if (cancelled) return;
        if (!found) {
          setError('Item not found.');
        } else {
          setForm({
            name: found.name ?? '',
            sku: found.sku ?? '',
            quantity: String(found.quantity ?? ''),
            location: found.location ?? '',
          });
        }
      } catch (err) {
        if (!cancelled && !handleApiError(err)) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isEdit, id, token, handleApiError]);

  /** Update a single form field by name. */
  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  /** Validate the form. Returns an error string, or empty string if valid. */
  function validate() {
    if (form.name.trim() === '') return 'Name is required.';
    if (form.sku.trim() === '') return 'SKU is required.';
    if (form.location.trim() === '') return 'Location is required.';
    if (form.quantity === '') return 'Quantity is required.';

    const quantity = Number(form.quantity);
    if (!Number.isInteger(quantity)) {
      return 'Quantity must be a whole number.';
    }
    if (quantity < 0) {
      return 'Quantity cannot be negative.';
    }
    return '';
  }

  /** Validate, then POST a new item or PUT an existing one. */
  async function handleSubmit(e) {
    e.preventDefault();

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = {
      name: form.name.trim(),
      sku: form.sku.trim(),
      quantity: Number(form.quantity),
      location: form.location.trim(),
    };

    setError('');
    setBusy(true);
    try {
      if (isEdit) {
        await apiRequest(`/api/inventory/${id}`, {
          method: 'PUT',
          body: payload,
          token,
        });
      } else {
        await apiRequest('/api/inventory', {
          method: 'POST',
          body: payload,
          token,
        });
      }
      navigate('/');
    } catch (err) {
      if (handleApiError(err)) return;
      if (err.status === 403) {
        setError('Only administrators can save inventory items.');
        return;
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-bar">
        <h1 className="app-bar-title">
          {isEdit ? 'Edit Item' : 'Add Item'}
        </h1>
      </header>

      <main className="content">
        {loading ? (
          <p className="muted-text">Loading item&hellip;</p>
        ) : (
          <form className="card form-card" onSubmit={handleSubmit}>
            <label className="field-label" htmlFor="name">
              Name
            </label>
            <input
              id="name"
              className="text-input"
              type="text"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
            />

            <label className="field-label" htmlFor="sku">
              SKU
            </label>
            <input
              id="sku"
              className="text-input"
              type="text"
              value={form.sku}
              onChange={(e) => updateField('sku', e.target.value)}
            />

            <label className="field-label" htmlFor="quantity">
              Quantity
            </label>
            <input
              id="quantity"
              className="text-input"
              type="number"
              min="0"
              step="1"
              value={form.quantity}
              onChange={(e) => updateField('quantity', e.target.value)}
            />

            <label className="field-label" htmlFor="location">
              Location
            </label>
            <input
              id="location"
              className="text-input"
              type="text"
              value={form.location}
              onChange={(e) => updateField('location', e.target.value)}
            />

            {error && <p className="error-message">{error}</p>}

            <div className="button-row">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={busy}
              >
                {isEdit ? 'Save Changes' : 'Create Item'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy}
                onClick={() => navigate('/')}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
