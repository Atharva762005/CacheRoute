// PropIQ Main App v4 — hamburger top-left, drawer panels, no left column
import React, { useState, useCallback, useRef, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import ChatWindow from './components/ChatWindow';
import PropertyForm from './components/PropertyForm';
import ResultsDashboard from './components/ResultsDashboard';
import ImageUpload from './components/ImageUpload';
import PropertyMap from './components/PropertyMap';
import BatchUpload from './components/BatchUpload';
import { assessFull, assessWithImages, downloadPDF } from './utils/api';
import './styles/global.css';

if (!window.L) {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(link);
  const script = document.createElement('script');
  script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  document.head.appendChild(script);
}

const DEFAULT_FORM = {
  locality: '', prop_type: '', size_sqft: '', age_years: '',
  floor_num: 3, is_freehold: 1, is_rera_registered: 1,
  occupancy: 'self_occupied', rental_yield_pct: 0,
};

// ── Animated Hamburger ──────────────────────────────────────────────────────
function HamburgerButton({ open, onClick }) {
  return (
    <button
      onClick={onClick}
      aria-label="Menu"
      style={{
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        alignItems: 'center', gap: 5, width: 38, height: 38,
        border: '1.5px solid rgba(83,74,183,0.25)', borderRadius: 9,
        background: open ? '#EEEDFE' : '#fff', cursor: 'pointer',
        transition: 'all 0.15s', flexShrink: 0,
      }}
    >
      {[0, 1, 2].map((i) => (
        <span key={i} style={{
          display: 'block', width: 16, height: 2, borderRadius: 2,
          background: '#534AB7', transition: 'all 0.2s',
          transform: open
            ? i === 0 ? 'translateY(7px) rotate(45deg)'
              : i === 2 ? 'translateY(-7px) rotate(-45deg)'
              : 'scaleX(0)'
            : 'none',
          opacity: open && i === 1 ? 0 : 1,
        }} />
      ))}
    </button>
  );
}

// ── Inline Panel Column ──────────────────────────────────────────────────────
function InlinePanel({ open, onClose, title, icon, width, children }) {
  return (
    <div style={{
      width: open ? width : 0,
      minWidth: open ? width : 0,
      overflow: 'hidden',
      flexShrink: 0,
      transition: 'width 0.28s cubic-bezier(0.4,0,0.2,1), min-width 0.28s cubic-bezier(0.4,0,0.2,1)',
      display: 'flex',
      flexDirection: 'column',
      background: '#fff',
      borderRight: '1px solid rgba(44,44,42,0.10)',
      boxShadow: open ? '2px 0 16px rgba(83,74,183,0.08)' : 'none',
    }}>
      {/* Panel header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 18px', borderBottom: '1px solid rgba(44,44,42,0.10)',
        background: '#FAFAF8', flexShrink: 0, minWidth: width,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>{icon}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#2C2C2A' }}>{title}</span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: '#F1EFE8', border: 'none', borderRadius: 7,
            width: 30, height: 30, fontSize: 17, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#5F5E5A', fontFamily: 'Inter, sans-serif',
          }}
        >×</button>
      </div>
      {/* Panel body */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: width }}>
        {children}
      </div>
    </div>
  );
}

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [images, setImages] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingPDF, setLoadingPDF] = useState(false);
  const [selectedCity, setSelectedCity] = useState('Pune');
  const [mode, setMode] = useState('single');
  const [menuOpen, setMenuOpen] = useState(false);
  const [drawer, setDrawer] = useState(null); // null | 'chat' | 'form'
  const [resolvedLocation, setResolvedLocation] = useState(null);
  const menuRef = useRef(null);

  // Close menu on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const openDrawer = (panel) => {
    setDrawer(panel);
    setMenuOpen(false);
  };

  const closeDrawer = () => setDrawer(null);

  const handleAssess = useCallback(async (options = {}) => {
    if (!form.locality || !form.prop_type || !form.size_sqft || form.age_years === '') {
      toast.error('Please fill: location, property type, size, and age');
      return;
    }
    setLoading(true);
    if (!options.keepDrawer) closeDrawer();
    try {
      const payload = resolvedLocation
        ? { ...form, geo_lat: resolvedLocation.lat, geo_lon: resolvedLocation.lon }
        : { ...form };

      let data;
      if (images.length > 0) {
        data = await assessWithImages(payload, images);
        const cond = data.cv_assessment?.condition?.toUpperCase();
        if (cond) toast.success(`CV: ${cond} detected (${images.length} image${images.length > 1 ? 's' : ''})`);
      } else {
        data = await assessFull(payload);
      }
      setResult(data);
      toast.success('Assessment complete!');
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || 'Assessment failed');
    } finally {
      setLoading(false);
    }
  }, [form, images, resolvedLocation]);

  const handlePDF = useCallback(async () => {
    if (!form.locality) { toast.error('Run an assessment first'); return; }
    setLoadingPDF(true);
    try { await downloadPDF(form); toast.success('PDF downloaded!'); }
    catch { toast.error('PDF generation failed'); }
    finally { setLoadingPDF(false); }
  }, [form]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh',
      background: '#F7F6F2', fontFamily: 'Inter, sans-serif', overflow: 'hidden' }}>

      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes menuIn { from { opacity:0; transform:translateY(-6px) } to { opacity:1; transform:translateY(0) } }
      `}</style>

      <Toaster position="top-right" toastOptions={{ duration: 3000,
        style: { fontFamily: 'Inter, sans-serif', fontSize: 13 } }} />

      {/* ── Navbar ──────────────────────────────────────────────── */}
      <nav style={{
        background: '#fff', borderBottom: '1px solid rgba(44,44,42,0.10)',
        padding: '0 16px', height: 54, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', flexShrink: 0, zIndex: 200,
      }}>

        {/* LEFT side: hamburger + logo + city + mode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>

          {/* Hamburger with dropdown */}
          <div ref={menuRef} style={{ position: 'relative' }}>
            <HamburgerButton open={menuOpen} onClick={() => setMenuOpen((o) => !o)} />

            {menuOpen && (
              <div style={{
                position: 'absolute', left: 0, top: 'calc(100% + 8px)',
                background: '#fff', border: '1px solid rgba(44,44,42,0.12)',
                borderRadius: 12, boxShadow: '0 12px 36px rgba(0,0,0,0.14)',
                overflow: 'hidden', minWidth: 200, zIndex: 500,
                animation: 'menuIn 0.18s ease',
              }}>
                {[
                  { k: 'chat', icon: '💬', label: 'Chat Assistant', desc: 'Natural language input' },
                  { k: 'form', icon: '📋', label: 'Property Form', desc: 'Structured field input' },
                ].map((item, idx) => (
                  <button
                    key={item.k}
                    onClick={() => openDrawer(item.k)}
                    style={{
                      width: '100%', padding: '12px 16px', border: 'none', textAlign: 'left',
                      background: drawer === item.k ? '#F3F1FE' : '#fff',
                      cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                      borderBottom: idx === 0 ? '1px solid rgba(44,44,42,0.07)' : 'none',
                      display: 'flex', alignItems: 'center', gap: 10,
                    }}
                  >
                    <span style={{
                      width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                      background: item.k === 'chat' ? '#EEEDFE' : '#E1F5EE',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
                    }}>{item.icon}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600,
                        color: drawer === item.k ? '#534AB7' : '#2C2C2A' }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: 10, color: '#888780', marginTop: 1 }}>
                        {item.desc}
                      </div>
                    </div>
                    {drawer === item.k && (
                      <span style={{ marginLeft: 'auto', fontSize: 9, fontWeight: 700,
                        color: '#534AB7', background: '#EEEDFE', borderRadius: 4,
                        padding: '2px 6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Open
                      </span>
                    )}
                  </button>
                ))}

                {/* Quick run button if form is filled */}
                {form.locality && (
                  <div style={{ padding: '10px 14px', borderTop: '1px solid rgba(44,44,42,0.07)',
                    background: '#FAFAF8' }}>
                    <button
                      onClick={() => { setMenuOpen(false); handleAssess(); }}
                      disabled={loading}
                      style={{
                        width: '100%', padding: '9px', border: 'none', borderRadius: 8,
                        background: loading ? '#C8C4EE' : '#534AB7', color: '#fff',
                        fontSize: 12, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
                        fontFamily: 'Inter, sans-serif',
                      }}
                    >
                      {loading ? 'Assessing…' : `⚡ Assess · ${form.locality}`}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, flexShrink: 0,
              background: 'linear-gradient(135deg, #534AB7, #0F6E56)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 800, fontSize: 13 }}>P</div>
            <div>
              <span style={{ fontWeight: 800, fontSize: 15, color: '#2C2C2A' }}>PropIQ</span>
              <span style={{ fontSize: 11, color: '#888780', marginLeft: 8 }}>
                AI Collateral Intelligence
              </span>
            </div>
          </div>

          {/* City selector */}
          <div style={{ display: 'flex', gap: 4, marginLeft: 8, background: '#F1EFE8',
            borderRadius: 8, padding: 3 }}>
            {['Pune', 'Mumbai', 'Bangalore'].map((city) => (
              <button key={city} onClick={() => setSelectedCity(city)}
                style={{ padding: '4px 12px', border: 'none', borderRadius: 6,
                  background: selectedCity === city ? '#fff' : 'transparent',
                  color: selectedCity === city ? '#534AB7' : '#888780',
                  fontSize: 11, fontWeight: selectedCity === city ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                  boxShadow: selectedCity === city ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.15s' }}>{city}</button>
            ))}
          </div>

          {/* Mode toggle */}
          <div style={{ display: 'flex', gap: 4, marginLeft: 4, background: '#F1EFE8',
            borderRadius: 8, padding: 3 }}>
            {[{ k: 'single', l: 'Single' }, { k: 'batch', l: 'Batch' }].map((m) => (
              <button key={m.k} onClick={() => setMode(m.k)}
                style={{ padding: '4px 12px', border: 'none', borderRadius: 6,
                  background: mode === m.k ? '#fff' : 'transparent',
                  color: mode === m.k ? '#534AB7' : '#888780',
                  fontSize: 11, fontWeight: mode === m.k ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                  boxShadow: mode === m.k ? '0 1px 3px rgba(0,0,0,0.08)' : 'none' }}>{m.l}</button>
            ))}
          </div>
        </div>

        {/* RIGHT: status pill + API docs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {form.locality && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5,
              background: '#E1F5EE', borderRadius: 20, padding: '3px 10px' }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#0F6E56' }} />
              <span style={{ fontSize: 11, color: '#0F6E56', fontWeight: 600 }}>
                {form.locality}
              </span>
              {images.length > 0 && (
                <span style={{ fontSize: 10, color: '#5F5E5A' }}>· 📷 {images.length}</span>
              )}
            </div>
          )}
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#0F6E56' }} />
          <span style={{ fontSize: 11, color: '#5F5E5A' }}>3 cities · 39 localities · MAPE 8.3%</span>
          <a href={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/docs`} target="_blank" rel="noreferrer"
            style={{ fontSize: 11, color: '#534AB7', textDecoration: 'none',
              padding: '4px 10px', background: '#EEEDFE', borderRadius: 6, fontWeight: 500 }}>
            API Docs ↗
          </a>
        </div>
      </nav>

      {/* (drawers removed — panels are now inline columns) */}

      {/* ── Main Content ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {mode === 'batch' ? (
          <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
            <BatchUpload onViewProperty={setResult} />
          </div>
        ) : (
          <>
            {/* ── Chat Assistant inline panel ──────────────────── */}
            <InlinePanel
              open={drawer === 'chat'}
              onClose={closeDrawer}
              title="Chat Assistant"
              icon="💬"
              width={360}
            >
              <ChatWindow
                form={form}
                onFormUpdate={setForm}
                onAssess={handleAssess}
                onPDF={handlePDF}
                loading={loading}
                result={result}
              />
            </InlinePanel>

            {/* ── Property Form inline panel ────────────────────── */}
            <InlinePanel
              open={drawer === 'form'}
              onClose={closeDrawer}
              title="Property Form"
              icon="📋"
              width={340}
            >
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <PropertyForm
                  form={form}
                  onChange={setForm}
                  onSubmit={handleAssess}
                  loading={loading}
                />
              </div>
            </InlinePanel>

            {/* ── Map + Images panel ───────────────────────────── */}
            <div style={{
              width: 300, flexShrink: 0,
              borderRight: '1px solid rgba(44,44,42,0.10)',
              background: '#FAFAF8', overflowY: 'auto', paddingTop: 16,
            }}>
              {/* Map with Address/Lat-Long tabs */}
              <PropertyMap
                locality={form.locality}
                result={result}
                city={selectedCity}
                onLocationResolved={setResolvedLocation}
              />

              {/* Multi-image upload */}
              <ImageUpload images={images} onImagesChange={setImages} />

              {/* Property summary card */}
              {form.locality && (
                <div style={{ margin: '0 20px 16px', background: '#fff',
                  border: '1px solid rgba(44,44,42,0.10)', borderRadius: 10,
                  padding: '12px 14px' }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#888780',
                    textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                    Selected Property
                  </div>
                  {[
                    ['City', selectedCity],
                    ['Locality', form.locality],
                    ['Type', form.prop_type?.replace(/_/g, ' ')],
                    ['Size', form.size_sqft ? `${form.size_sqft} sqft` : null],
                    ['Age', form.age_years !== '' ? `${form.age_years} yrs` : null],
                    ['Title', form.is_freehold ? 'Freehold' : 'Leasehold'],
                    resolvedLocation
                      ? ['Pinned', `${resolvedLocation.lat?.toFixed(4)}, ${resolvedLocation.lon?.toFixed(4)}`]
                      : null,
                  ]
                    .filter((r) => r && r[1])
                    .map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between',
                        fontSize: 12, padding: '3px 0',
                        borderBottom: '1px solid rgba(44,44,42,0.05)' }}>
                        <span style={{ color: '#888780' }}>{k}</span>
                        <span style={{ fontWeight: 500, color: '#2C2C2A',
                          textTransform: 'capitalize' }}>{v}</span>
                      </div>
                    ))}
                  {images.length > 0 && (
                    <div style={{ marginTop: 8, fontSize: 11, color: '#0F6E56', fontWeight: 600,
                      textAlign: 'center', background: '#E1F5EE', borderRadius: 6, padding: 4 }}>
                      📷 {images.length} image{images.length > 1 ? 's' : ''} · CV Active
                    </div>
                  )}
                </div>
              )}

              {/* Quick action buttons */}
              <div style={{ padding: '0 20px 16px', display: 'flex', gap: 8 }}>
                <button
                  onClick={() => openDrawer('chat')}
                  style={{ flex: 1, padding: '9px', border: '1.5px solid #534AB7',
                    borderRadius: 8,
                    background: drawer === 'chat' ? '#534AB7' : '#EEEDFE',
                    color: drawer === 'chat' ? '#fff' : '#534AB7',
                    fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'Inter, sans-serif', transition: 'all 0.15s' }}
                >
                  💬 Chat
                </button>
                <button
                  onClick={() => openDrawer('form')}
                  style={{ flex: 1, padding: '9px', border: '1.5px solid #0F6E56',
                    borderRadius: 8,
                    background: drawer === 'form' ? '#0F6E56' : '#E1F5EE',
                    color: drawer === 'form' ? '#fff' : '#0F6E56',
                    fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'Inter, sans-serif', transition: 'all 0.15s' }}
                >
                  📋 Form
                </button>
              </div>

              {/* Run Assessment button */}
              {form.locality && (
                <div style={{ padding: '0 20px 20px' }}>
                  <button
                    onClick={handleAssess}
                    disabled={loading}
                    style={{
                      width: '100%', padding: '11px', border: 'none', borderRadius: 10,
                      background: loading ? '#AFA9EC' : 'linear-gradient(135deg,#534AB7,#3C3489)',
                      color: '#fff', fontSize: 13, fontWeight: 700,
                      cursor: loading ? 'not-allowed' : 'pointer',
                      fontFamily: 'Inter, sans-serif', letterSpacing: '0.02em',
                      boxShadow: loading ? 'none' : '0 4px 14px rgba(83,74,183,0.35)',
                      transition: 'all 0.2s',
                    }}
                  >
                    {loading ? 'Assessing…' : '⚡ Run Assessment'}
                  </button>
                </div>
              )}
            </div>

            {/* ── Results panel ────────────────────────────────── */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {result ? (
                <ResultsDashboard result={result} onDownloadPDF={handlePDF} loadingPDF={loadingPDF} />
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', padding: 40, textAlign: 'center' }}>
                  <div style={{ width: 80, height: 80, borderRadius: 22, marginBottom: 24,
                    background: 'linear-gradient(135deg,#EEEDFE,#E1F5EE)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 38 }}>
                    🏠
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#2C2C2A', marginBottom: 10 }}>
                    AI Collateral Assessment
                  </div>
                  <div style={{ fontSize: 13, color: '#888780', maxWidth: 400,
                    lineHeight: 1.8, marginBottom: 28 }}>
                    Click <strong style={{ color: '#534AB7' }}>☰</strong> in the top-left to open{' '}
                    <span style={{ color: '#534AB7', fontWeight: 600, cursor: 'pointer' }}
                      onClick={() => openDrawer('chat')}>Chat</span>{' '}or{' '}
                    <span style={{ color: '#534AB7', fontWeight: 600, cursor: 'pointer' }}
                      onClick={() => openDrawer('form')}>Form</span>.
                    Pin a location with Address or Lat-Long, optionally add exterior/interior photos, then run.
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10,
                    width: '100%', maxWidth: 520 }}>
                    {[
                      ['⚡', 'Sub-90 sec assessment'], ['📊', 'P10/P50/P90 range'],
                      ['🔍', 'SHAP explainability'], ['📋', 'RBI-ready PDF'],
                      ['📷', 'Multi-image CV scoring'], ['🏘', 'Comparable sales'],
                      ['📍', 'Address/Lat-Long pin'], ['💰', 'LTV calculation'],
                      ['📈', '24-month price trend'],
                    ].map(([icon, text]) => (
                      <div key={text} style={{ background: '#fff',
                        border: '1px solid rgba(44,44,42,0.08)', borderRadius: 10,
                        padding: '11px 14px', display: 'flex', alignItems: 'center',
                        gap: 8, fontSize: 12, color: '#5F5E5A' }}>
                        <span style={{ fontSize: 16 }}>{icon}</span>{text}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}