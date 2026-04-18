// PropIQ ResultsDashboard Component
import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, ReferenceLine } from 'recharts';
import CompsPanel from './CompsPanel';
import PriceTrendChart from './PriceTrendChart';
import LTVCalculator from './LTVCalculator';
import CreditMemoPanel from './CreditMemoPanel';
import { formatINR, formatINRShort } from '../utils/api';

// ── Helpers ────────────────────────────────────────────────────────────────

const rpiColor = (rpi) => {
  if (rpi >= 75) return { bg: '#E1F5EE', text: '#085041', bar: '#0F6E56', label: 'Highly Liquid' };
  if (rpi >= 50) return { bg: '#FAEEDA', text: '#633806', bar: '#BA7517', label: 'Moderate Liquidity' };
  return      { bg: '#FCEBEB', text: '#791F1F', bar: '#A32D2D', label: 'Illiquid' };
};

const severityStyle = (sev) => ({
  high:   { bg: '#FCEBEB', border: '#F09595', text: '#791F1F', dot: '#A32D2D' },
  medium: { bg: '#FAEEDA', border: '#FAC775', text: '#633806', dot: '#BA7517' },
  low:    { bg: '#F1EFE8', border: '#D3D1C7', text: '#444441', dot: '#888780' },
}[sev] || { bg: '#F1EFE8', border: '#D3D1C7', text: '#444441', dot: '#888780' });

const MetricCard = ({ label, value, sub, accent }) => (
  <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
    borderRadius: 12, padding: '14px 16px', borderTop: `3px solid ${accent || '#534AB7'}` }}>
    <div style={{ fontSize: 11, fontWeight: 600, color: '#888780',
      textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 700, color: '#2C2C2A', lineHeight: 1.2 }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#888780', marginTop: 4 }}>{sub}</div>}
  </div>
);

// ── SHAP Waterfall Chart ───────────────────────────────────────────────────

function ShapWaterfall({ drivers }) {
  if (!drivers || drivers.length === 0) return null;

  // Build waterfall data
  let running = 0;
  const chartData = drivers.slice(0, 6).map((d) => {
    const start = running;
    running += d.impact_inr;
    return {
      feature: d.feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      impact: d.impact_inr,
      start: d.impact_inr >= 0 ? start : start + d.impact_inr,
      end: running,
      positive: d.impact_inr >= 0,
    };
  });

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.12)',
        borderRadius: 8, padding: '10px 14px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.feature}</div>
        <div style={{ color: d.positive ? '#0F6E56' : '#A32D2D', fontWeight: 700 }}>
          {d.positive ? '+' : ''}{formatINR(d.impact)}
        </div>
      </div>
    );
  };

  return (
    <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
      borderRadius: 12, padding: '18px 18px 12px', marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>SHAP Value Drivers</div>
      <div style={{ fontSize: 11, color: '#888780', marginBottom: 14 }}>
        How each feature contributes to the final valuation
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ left: 10, right: 10, top: 4, bottom: 40 }}>
          <XAxis dataKey="feature" tick={{ fontSize: 10, fill: '#888780' }}
            angle={-30} textAnchor="end" interval={0} />
          <YAxis tickFormatter={v => formatINRShort(Math.abs(v))}
            tick={{ fontSize: 10, fill: '#888780' }} width={55} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="rgba(44,44,42,0.15)" />
          <Bar dataKey="impact" radius={[4, 4, 0, 0]}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={d.positive ? '#0F6E56' : '#A32D2D'} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── RPI Gauge ──────────────────────────────────────────────────────────────

function RPIGauge({ rpi }) {
  const col = rpiColor(rpi);
  const pct = rpi / 100;
  const r = 44, cx = 56, cy = 56;
  const circumference = Math.PI * r; // semicircle
  const offset = circumference * (1 - pct);

  return (
    <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
      borderRadius: 12, padding: '16px', textAlign: 'center' }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#888780',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        Resale Potential Index
      </div>
      <svg width={112} height={74} style={{ display: 'block', margin: '0 auto' }}>
        {/* Track */}
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke="#F1EFE8" strokeWidth={10} strokeLinecap="round" />
        {/* Fill */}
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke={col.bar} strokeWidth={10} strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize={22} fontWeight={700}
          fill="#2C2C2A">{Math.round(rpi)}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontSize={10} fill="#888780">/100</text>
      </svg>
      <div style={{ marginTop: 8, fontSize: 12, fontWeight: 600,
        color: col.text, background: col.bg, borderRadius: 20, padding: '3px 10px',
        display: 'inline-block' }}>{col.label}</div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────

export default function ResultsDashboard({ result, onDownloadPDF, loadingPDF }) {
  const [tab, setTab] = useState('overview');
  if (!result) return null;

  const {
    locality, prop_type, size_sqft, market_value_range, market_value_mid,
    distress_value_range, resale_potential_index, estimated_time_to_sell_days,
    confidence_score, price_per_sqft_estimate, key_drivers, risk_flags,
    enrichment, cv_assessment, processing_time_ms, model_mape_pct, request_id,
  } = result;

  const rpiCol = rpiColor(resale_potential_index);
  const tabs = ['overview', 'drivers', 'risk', 'comps', 'trends', 'ltv', 'memo', 'data'];

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '16px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#2C2C2A' }}>
            {prop_type?.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())} — {locality}
          </div>
          <div style={{ fontSize: 11, color: '#888780', marginTop: 2 }}>
            {size_sqft?.toLocaleString()} sqft · ID: {request_id} · {processing_time_ms}ms · MAPE {model_mape_pct}%
          </div>
        </div>
        <button onClick={onDownloadPDF} disabled={loadingPDF}
          style={{ padding: '8px 14px', background: loadingPDF ? '#D3D1C7' : '#0F6E56',
            color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 600,
            cursor: loadingPDF ? 'not-allowed' : 'pointer', fontFamily: 'Inter, sans-serif',
            display: 'flex', alignItems: 'center', gap: 5 }}>
          {loadingPDF ? '...' : '⬇ PDF Report'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 14, background: '#F1EFE8',
        padding: 4, borderRadius: 10 }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ flex: 1, padding: '7px 0', border: 'none',
              background: tab === t ? '#fff' : 'transparent',
              borderRadius: 7, fontSize: 11, fontWeight: tab === t ? 600 : 400,
              color: tab === t ? '#534AB7' : '#888780', cursor: 'pointer',
              fontFamily: 'Inter, sans-serif', textTransform: 'capitalize',
              boxShadow: tab === t ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s' }}>{t}</button>
        ))}
      </div>

      {/* ── Overview Tab ─────────────────────────────────────────────── */}
      {tab === 'overview' && (
        <div>
          {/* Market Value Hero */}
          <div style={{ background: 'linear-gradient(135deg, #534AB7 0%, #3C3489 100%)',
            borderRadius: 14, padding: '20px 20px 16px', marginBottom: 14, color: '#fff' }}>
            <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.75,
              textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
              Market Value Estimate
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-0.02em' }}>
              {formatINR(market_value_mid)}
            </div>
            <div style={{ fontSize: 13, opacity: 0.8, marginTop: 4 }}>
              Range: {formatINR(market_value_range?.[0])} — {formatINR(market_value_range?.[1])}
            </div>
            <div style={{ marginTop: 12, paddingTop: 12,
              borderTop: '1px solid rgba(255,255,255,0.15)',
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div>
                <div style={{ fontSize: 10, opacity: 0.65, marginBottom: 2 }}>Distress Value</div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  {formatINR(distress_value_range?.[0])} — {formatINR(distress_value_range?.[1])}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 10, opacity: 0.65, marginBottom: 2 }}>Price / sqft</div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  ₹{price_per_sqft_estimate?.toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          {/* Metrics grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
            <RPIGauge rpi={resale_potential_index} />
            <MetricCard label="Time to Liquidate"
              value={`${estimated_time_to_sell_days?.[0]}–${estimated_time_to_sell_days?.[1]} days`}
              sub="Expected market absorption" accent="#BA7517" />
            <MetricCard label="Confidence Score"
              value={`${Math.round((confidence_score || 0) * 100)}%`}
              sub={confidence_score >= 0.8 ? 'High confidence' : confidence_score >= 0.6 ? 'Medium' : 'Low'}
              accent={confidence_score >= 0.8 ? '#0F6E56' : '#BA7517'} />
            <MetricCard label="Risk Flags"
              value={risk_flags?.length || 0}
              sub={risk_flags?.length === 0 ? 'No issues detected' : `${risk_flags?.filter(f=>f.severity==='high').length} high severity`}
              accent={risk_flags?.length === 0 ? '#0F6E56' : '#A32D2D'} />
          </div>

          {/* CV Assessment — rich panel */}
          {cv_assessment?.image_analyzed && (
            <div style={{ marginBottom: 14 }}>
              {/* Header */}
              <div style={{ background: 'linear-gradient(135deg,#534AB7,#3C3489)',
                borderRadius: '12px 12px 0 0', padding: '10px 16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ color: '#fff', fontSize: 12, fontWeight: 700 }}>
                  📷 CV Condition Assessment
                </div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.75)' }}>
                  {cv_assessment.images_count || 1} image{(cv_assessment.images_count||1) > 1 ? 's' : ''} analysed ·{' '}
                  {cv_assessment.weighting || 'Single image'}
                </div>
              </div>

              {/* Body */}
              <div style={{ background: '#EEEDFE', border: '1px solid #CECBF6',
                borderTop: 'none', borderRadius: '0 0 12px 12px', padding: '12px 16px' }}>

                {/* Composite condition + quality */}
                <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
                  {/* Condition badge */}
                  <div style={{ flex: 1, background: '#fff', borderRadius: 10,
                    padding: '10px 12px', textAlign: 'center',
                    border: `2px solid ${
                      cv_assessment.condition === 'excellent' ? '#0F6E56' :
                      cv_assessment.condition === 'good' ? '#534AB7' :
                      cv_assessment.condition === 'fair' ? '#BA7517' : '#A32D2D'}` }}>
                    <div style={{ fontSize: 11, color: '#888780', marginBottom: 3 }}>Composite</div>
                    <div style={{ fontSize: 16, fontWeight: 800, textTransform: 'uppercase',
                      color: cv_assessment.condition === 'excellent' ? '#0F6E56' :
                             cv_assessment.condition === 'good' ? '#534AB7' :
                             cv_assessment.condition === 'fair' ? '#BA7517' : '#A32D2D' }}>
                      {cv_assessment.condition}
                    </div>
                  </div>
                  {/* Quality score */}
                  <div style={{ flex: 1, background: '#fff', borderRadius: 10,
                    padding: '10px 12px', textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: '#888780', marginBottom: 3 }}>Quality</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#2C2C2A' }}>
                      {cv_assessment.quality_score?.toFixed(0)}<span style={{ fontSize: 11 }}>/100</span>
                    </div>
                  </div>
                  {/* Confidence */}
                  <div style={{ flex: 1, background: '#fff', borderRadius: 10,
                    padding: '10px 12px', textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: '#888780', marginBottom: 3 }}>Confidence</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#2C2C2A' }}>
                      {Math.round((cv_assessment.cv_confidence || 0) * 100)}%
                    </div>
                  </div>
                </div>

                {/* Exterior / Interior split (when multi-image) */}
                {cv_assessment.exterior_condition && cv_assessment.interior_condition && (
                  <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                    <div style={{ flex: 1, background: 'rgba(255,255,255,0.7)',
                      borderRadius: 8, padding: '7px 10px', fontSize: 12 }}>
                      <span style={{ color: '#888780' }}>🏢 Exterior: </span>
                      <strong style={{ textTransform: 'capitalize' }}>{cv_assessment.exterior_condition}</strong>
                      <span style={{ color: '#888780', fontSize: 10 }}> (60% weight)</span>
                    </div>
                    <div style={{ flex: 1, background: 'rgba(255,255,255,0.7)',
                      borderRadius: 8, padding: '7px 10px', fontSize: 12 }}>
                      <span style={{ color: '#888780' }}>🛋 Interior: </span>
                      <strong style={{ textTransform: 'capitalize' }}>{cv_assessment.interior_condition}</strong>
                      <span style={{ color: '#888780', fontSize: 10 }}> (40% weight)</span>
                    </div>
                  </div>
                )}

                {/* Adjustment banner */}
                <div style={{
                  background: cv_assessment.valuation_adjustment_factor > 1
                    ? 'rgba(15,110,86,0.12)' : cv_assessment.valuation_adjustment_factor < 1
                    ? 'rgba(163,45,45,0.10)' : 'rgba(83,74,183,0.08)',
                  borderRadius: 8, padding: '8px 12px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <span style={{ fontSize: 12, color: '#2C2C2A' }}>
                    Valuation Adjustment
                  </span>
                  <span style={{ fontWeight: 800, fontSize: 14,
                    color: cv_assessment.valuation_adjustment_factor > 1 ? '#0F6E56'
                         : cv_assessment.valuation_adjustment_factor < 1 ? '#A32D2D' : '#534AB7' }}>
                    {cv_assessment.valuation_adjustment_factor > 1 ? '+' : ''}
                    {((cv_assessment.valuation_adjustment_factor - 1) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* ── Drivers Tab ──────────────────────────────────────────────── */}
      {tab === 'drivers' && (
        <div>
          <ShapWaterfall drivers={key_drivers} />
          <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
            borderRadius: 12, overflow: 'hidden' }}>
            {key_drivers?.map((d, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '11px 16px',
                borderBottom: i < key_drivers.length - 1 ? '1px solid rgba(44,44,42,0.07)' : 'none',
                background: i % 2 === 0 ? '#fff' : '#FAFAF8' }}>
                <div style={{ fontSize: 13, color: '#2C2C2A' }}>
                  {d.feature.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())}
                </div>
                <div style={{ fontWeight: 700, fontSize: 13,
                  color: d.direction === 'positive' ? '#0F6E56' : '#A32D2D' }}>
                  {d.direction === 'positive' ? '+' : '–'} {formatINR(Math.abs(d.impact_inr))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Risk Tab ─────────────────────────────────────────────────── */}
      {tab === 'risk' && (
        <div>
          {risk_flags?.length === 0 ? (
            <div style={{ background: '#E1F5EE', border: '1px solid #9FE1CB',
              borderRadius: 12, padding: '20px', textAlign: 'center' }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>✓</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#085041' }}>
                No risk flags detected
              </div>
              <div style={{ fontSize: 12, color: '#0F6E56', marginTop: 4 }}>
                All automated checks passed
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {risk_flags?.map((f, i) => {
                const s = severityStyle(f.severity);
                return (
                  <div key={i} style={{ background: s.bg, border: `1px solid ${s.border}`,
                    borderRadius: 12, padding: '12px 16px', borderLeft: `4px solid ${s.dot}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between',
                      alignItems: 'center', marginBottom: 4 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: s.text }}>
                        {f.flag.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                        color: s.text, background: 'rgba(255,255,255,0.6)',
                        padding: '2px 8px', borderRadius: 20 }}>{f.severity}</span>
                    </div>
                    <div style={{ fontSize: 12, color: s.text, opacity: 0.85, lineHeight: 1.5 }}>
                      {f.detail}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Enrichment Tab ───────────────────────────────────────────── */}
      {tab === 'enrichment' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              { label: 'Zone Tier', value: enrichment?.zone_tier?.toUpperCase(), accent: '#534AB7' },
              { label: 'Circle Rate', value: `₹${enrichment?.circle_rate_per_sqft?.toLocaleString()}/sqft`, accent: '#534AB7' },
              { label: 'Infra Score', value: `${enrichment?.infra_score?.toFixed(0)}/100`, accent: '#0F6E56' },
              { label: 'Listing Density', value: `${((enrichment?.listing_density || 0) * 100).toFixed(0)}%`, accent: '#BA7517' },
            ].map((m, i) => <MetricCard key={i} {...m} />)}
          </div>
          {enrichment?.geo?.lat && (
            <div style={{ marginTop: 10, background: '#F7F6F2', borderRadius: 10,
              padding: '10px 14px', fontSize: 12, color: '#5F5E5A' }}>
              📍 Coordinates: {enrichment.geo.lat?.toFixed(4)}, {enrichment.geo.lon?.toFixed(4)}
              {enrichment.geo.source && ` · Source: ${enrichment.geo.source}`}
            </div>
          )}
          <div style={{ marginTop: 10, background: '#F7F6F2', borderRadius: 10,
            padding: '10px 14px', fontSize: 11, color: '#888780' }}>
            Data sources: IGR Maharashtra circle rates, OpenStreetMap Overpass API,
            Nominatim geocoding. Model MAPE: {model_mape_pct}%.
          </div>
        </div>
      )}

      {tab === 'comps' && (
        <CompsPanel comps={result.comps} compStats={result.comp_stats} locality={locality} />
      )}

      {tab === 'trends' && (
        <div style={{ padding: '0 2px' }}>
          <PriceTrendChart locality={locality} propType={prop_type} />
        </div>
      )}

      {tab === 'ltv' && (
        <LTVCalculator ltvAnalysis={result.ltv_analysis} marketValueMid={market_value_mid} />
      )}

      {tab === 'memo' && (
        <CreditMemoPanel creditMemo={result.credit_memo} requestId={result.request_id} locality={locality} />
      )}

      {tab === 'data' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              { label: 'Zone Tier', value: enrichment?.zone_tier?.toUpperCase(), accent: '#534AB7' },
              { label: 'Circle Rate', value: `₹${enrichment?.circle_rate_per_sqft?.toLocaleString()}/sqft`, accent: '#534AB7' },
              { label: 'Infra Score', value: `${enrichment?.infra_score?.toFixed(0)}/100`, accent: '#0F6E56' },
              { label: 'Listing Density', value: `${((enrichment?.listing_density || 0) * 100).toFixed(0)}%`, accent: '#BA7517' },
            ].map((m, i) => <MetricCard key={i} {...m} />)}
          </div>
          {enrichment?.geo?.lat && (
            <div style={{ marginTop: 10, background: '#F7F6F2', borderRadius: 10,
              padding: '10px 14px', fontSize: 12, color: '#5F5E5A' }}>
              Coordinates: {enrichment.geo.lat?.toFixed(4)}, {enrichment.geo.lon?.toFixed(4)}
              {enrichment.geo.source && ` · Source: ${enrichment.geo.source}`}
            </div>
          )}
          <div style={{ marginTop: 10, background: '#F7F6F2', borderRadius: 10,
            padding: '10px 14px', fontSize: 11, color: '#888780' }}>
            Sources: IGR circle rates, OpenStreetMap, Nominatim. MAPE: {model_mape_pct}%.
          </div>
        </div>
      )}
    </div>
  );
}