// PropIQ PropertyForm — location via Address / Lat-Long tabs (replaces locality dropdown)
import React, { useState, useCallback } from 'react';
import { PROP_TYPES } from '../utils/api';
import { geocodeAddress, findNearestLocality } from '../utils/geo';

const s = {
  label: {
    fontSize: 11, fontWeight: 600, color: '#5F5E5A', textTransform: 'uppercase',
    letterSpacing: '0.06em', marginBottom: 5, display: 'block',
  },
  input: {
    width: '100%', padding: '9px 11px', border: '1px solid rgba(44,44,42,0.15)',
    borderRadius: 8, fontSize: 13, color: '#2C2C2A', background: '#fff',
    outline: 'none', transition: 'border-color 0.15s', fontFamily: 'Inter, sans-serif',
    boxSizing: 'border-box',
  },
  row: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 },
  full: { marginBottom: 14 },
  toggle: { display: 'flex', gap: 8 },
  toggleBtn: (active) => ({
    flex: 1, padding: '8px 0', border: `1.5px solid ${active ? '#534AB7' : 'rgba(44,44,42,0.15)'}`,
    borderRadius: 8, background: active ? '#EEEDFE' : '#fff',
    color: active ? '#3C3489' : '#5F5E5A', fontWeight: active ? 600 : 400,
    fontSize: 12, cursor: 'pointer', transition: 'all 0.15s', fontFamily: 'Inter, sans-serif',
  }),
};

const tabBtn = (active) => ({
  flex: 1, padding: '7px 0', border: 'none',
  background: active ? '#534AB7' : 'transparent',
  color: active ? '#fff' : '#888780',
  fontSize: 11, fontWeight: active ? 600 : 400,
  cursor: 'pointer', fontFamily: 'Inter, sans-serif',
  borderRadius: 6, transition: 'all 0.15s',
});

const locateBtn = (disabled) => ({
  padding: '9px 14px', border: 'none', borderRadius: 8,
  background: disabled ? '#C8C4EE' : '#534AB7',
  color: '#fff', fontSize: 12, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
  fontFamily: 'Inter, sans-serif', whiteSpace: 'nowrap', flexShrink: 0,
});

export default function PropertyForm({ form, onChange, onSubmit, loading }) {
  const set = (k, v) => onChange({ ...form, [k]: v });

  // Location tab state
  const [locMode, setLocMode] = useState('address');
  const [addressInput, setAddressInput] = useState('');
  const [latInput, setLatInput] = useState('');
  const [lngInput, setLngInput] = useState('');
  const [resolving, setResolving] = useState(false);
  const [locError, setLocError] = useState('');
  const [resolvedInfo, setResolvedInfo] = useState(null); // { locality, distKm, display }

  const applyLocation = useCallback(
    (lat, lon, display = '') => {
      const { locality, distanceKm } = findNearestLocality(lat, lon);
      setResolvedInfo({ locality, distKm: distanceKm.toFixed(1), display });
      onChange({ ...form, locality, geo_lat: lat, geo_lon: lon });
    },
    [form, onChange]
  );

  const handleGeocode = useCallback(async () => {
    const q = addressInput.trim();
    if (!q) return;
    setResolving(true);
    setLocError('');
    try {
      const geo = await geocodeAddress(q);
      if (!geo) { setLocError('Address not found. Try a more specific query.'); return; }
      applyLocation(geo.lat, geo.lon, geo.display);
    } catch {
      setLocError('Geocoding failed. Check your internet connection.');
    } finally {
      setResolving(false);
    }
  }, [addressInput, applyLocation]);

  const handleLatLng = useCallback(() => {
    const lat = parseFloat(latInput);
    const lon = parseFloat(lngInput);
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setLocError('Enter valid latitude (−90 to 90) and longitude (−180 to 180).');
      return;
    }
    setLocError('');
    applyLocation(lat, lon, `${lat.toFixed(5)}, ${lon.toFixed(5)}`);
  }, [latInput, lngInput, applyLocation]);

  const clearLocation = () => {
    setResolvedInfo(null);
    setAddressInput('');
    setLatInput('');
    setLngInput('');
    setLocError('');
    onChange({ ...form, locality: '', geo_lat: undefined, geo_lon: undefined });
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
      style={{ padding: '20px 20px 8px', overflowY: 'auto', flex: 1 }}
    >
      {/* ── Location Section ──────────────────────────────────── */}
      <div style={s.full}>
        <label style={s.label}>Location *</label>

        {/* Tab row */}
        <div style={{
          display: 'flex', background: '#F1EFE8', borderRadius: 8,
          padding: 3, gap: 3, marginBottom: 8,
        }}>
          <button type="button" style={tabBtn(locMode === 'address')}
            onClick={() => { setLocMode('address'); setLocError(''); }}>
            📍 Address
          </button>
          <button type="button" style={tabBtn(locMode === 'latlong')}
            onClick={() => { setLocMode('latlong'); setLocError(''); }}>
            🎯 Lat-Long
          </button>
        </div>

        {/* Address input */}
        {locMode === 'address' && (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              style={{ ...s.input, flex: 1 }}
              placeholder="e.g. Baner, Pune or full address"
              value={addressInput}
              onChange={(e) => setAddressInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGeocode()}
            />
            <button type="button" style={locateBtn(resolving || !addressInput.trim())}
              disabled={resolving || !addressInput.trim()}
              onClick={handleGeocode}>
              {resolving ? '…' : 'Locate'}
            </button>
          </div>
        )}

        {/* Lat-Long inputs */}
        {locMode === 'latlong' && (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              style={{ ...s.input, flex: 1 }}
              placeholder="Latitude e.g. 18.5362"
              type="number" step="0.0001"
              value={latInput}
              onChange={(e) => setLatInput(e.target.value)}
            />
            <input
              style={{ ...s.input, flex: 1 }}
              placeholder="Longitude e.g. 73.8938"
              type="number" step="0.0001"
              value={lngInput}
              onChange={(e) => setLngInput(e.target.value)}
            />
            <button type="button" style={locateBtn(!latInput || !lngInput)}
              disabled={!latInput || !lngInput}
              onClick={handleLatLng}>
              Pin
            </button>
          </div>
        )}

        {/* Error */}
        {locError && (
          <div style={{ fontSize: 10, color: '#c0392b', background: '#fdecea',
            borderRadius: 6, padding: '4px 8px', marginTop: 6 }}>
            ⚠ {locError}
          </div>
        )}

        {/* Resolved locality badge */}
        {resolvedInfo && (
          <div style={{ marginTop: 8, background: '#E1F5EE', borderRadius: 8,
            padding: '8px 10px', display: 'flex', alignItems: 'flex-start',
            justifyContent: 'space-between', gap: 8 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#0F6E56' }}>
                ✓ {resolvedInfo.locality}
              </div>
              <div style={{ fontSize: 10, color: '#3a8a6e', marginTop: 2, lineHeight: 1.4 }}>
                Nearest locality · {resolvedInfo.distKm} km away
              </div>
              {resolvedInfo.display && resolvedInfo.display !== resolvedInfo.locality && (
                <div style={{ fontSize: 9, color: '#888780', marginTop: 2,
                  maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {resolvedInfo.display}
                </div>
              )}
            </div>
            <button type="button" onClick={clearLocation}
              style={{ background: 'none', border: 'none', color: '#888780',
                cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0, flexShrink: 0 }}>
              ×
            </button>
          </div>
        )}
      </div>

      {/* ── Property Type ─────────────────────────────────────── */}
      <div style={s.full}>
        <label style={s.label}>Property Type *</label>
        <select value={form.prop_type || ''} onChange={(e) => set('prop_type', e.target.value)}
          style={s.input} required>
          <option value="">Select type...</option>
          {PROP_TYPES.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* ── Size + Age ────────────────────────────────────────── */}
      <div style={s.row}>
        <div>
          <label style={s.label}>Size (sqft) *</label>
          <input type="number" min="100" max="50000" placeholder="e.g. 850"
            value={form.size_sqft || ''}
            onChange={(e) => set('size_sqft', parseFloat(e.target.value))}
            style={s.input} required />
        </div>
        <div>
          <label style={s.label}>Age (years) *</label>
          <input type="number" min="0" max="80" placeholder="e.g. 8"
            value={form.age_years !== undefined ? form.age_years : ''}
            onChange={(e) => set('age_years', parseFloat(e.target.value))}
            style={s.input} required />
        </div>
      </div>

      {/* ── Floor + Rental Yield ──────────────────────────────── */}
      <div style={s.row}>
        <div>
          <label style={s.label}>Floor Number</label>
          <input type="number" min="0" max="50" placeholder="e.g. 3"
            value={form.floor_num !== undefined ? form.floor_num : ''}
            onChange={(e) => set('floor_num', parseInt(e.target.value))}
            style={s.input} />
        </div>
        <div>
          <label style={s.label}>Rental Yield %</label>
          <input type="number" min="0" max="15" step="0.1" placeholder="0.0"
            value={form.rental_yield_pct || ''}
            onChange={(e) => set('rental_yield_pct', parseFloat(e.target.value) || 0)}
            style={s.input} />
        </div>
      </div>

      {/* ── Title Type ────────────────────────────────────────── */}
      <div style={s.full}>
        <label style={s.label}>Title Type</label>
        <div style={s.toggle}>
          <button type="button" style={s.toggleBtn(form.is_freehold !== 0)}
            onClick={() => set('is_freehold', 1)}>Freehold</button>
          <button type="button" style={s.toggleBtn(form.is_freehold === 0)}
            onClick={() => set('is_freehold', 0)}>Leasehold</button>
        </div>
      </div>

      {/* ── RERA ──────────────────────────────────────────────── */}
      <div style={s.full}>
        <label style={s.label}>RERA Registered</label>
        <div style={s.toggle}>
          <button type="button" style={s.toggleBtn(form.is_rera_registered !== 0)}
            onClick={() => set('is_rera_registered', 1)}>Yes</button>
          <button type="button" style={s.toggleBtn(form.is_rera_registered === 0)}
            onClick={() => set('is_rera_registered', 0)}>No</button>
        </div>
      </div>

      {/* ── Occupancy ─────────────────────────────────────────── */}
      <div style={{ ...s.full, marginBottom: 20 }}>
        <label style={s.label}>Occupancy</label>
        <div style={s.toggle}>
          {['self_occupied', 'rented', 'vacant'].map((o) => (
            <button key={o} type="button"
              style={s.toggleBtn(form.occupancy === o)}
              onClick={() => set('occupancy', o)}>
              {o.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* ── Submit ────────────────────────────────────────────── */}
      <button type="submit" disabled={loading || !form.locality}
        style={{
          width: '100%', padding: '12px', border: 'none', borderRadius: 10,
          background: loading || !form.locality ? '#C8C4EE' : '#534AB7',
          color: '#fff', fontSize: 14, fontWeight: 600,
          cursor: loading || !form.locality ? 'not-allowed' : 'pointer',
          letterSpacing: '0.02em', fontFamily: 'Inter, sans-serif',
          transition: 'background 0.2s',
        }}>
        {loading ? 'Assessing…' : !form.locality ? 'Set location first' : '⚡ Run Assessment'}
      </button>
    </form>
  );
}