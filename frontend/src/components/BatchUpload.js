import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { formatINR, formatINRShort } from '../utils/api';
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const SAMPLE_CSV = `locality,prop_type,size_sqft,age_years,floor_num,is_freehold,is_rera_registered
Baner,2bhk_apartment,850,8,5,1,1
Kothrud,3bhk_apartment,1200,5,8,1,1
Wakad,2bhk_apartment,750,10,3,1,0
Hadapsar,shop,400,6,0,1,1
Viman Nagar,office,1000,4,7,1,1`;

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim());
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i]; });
    return {
      locality: obj.locality || '',
      prop_type: obj.prop_type || '2bhk_apartment',
      size_sqft: parseFloat(obj.size_sqft) || 800,
      age_years: parseFloat(obj.age_years) || 10,
      floor_num: parseInt(obj.floor_num) || 3,
      is_freehold: parseInt(obj.is_freehold) ?? 1,
      is_rera_registered: parseInt(obj.is_rera_registered) ?? 1,
      occupancy: obj.occupancy || 'self_occupied',
      rental_yield_pct: parseFloat(obj.rental_yield_pct) || 0,
    };
  }).filter(r => r.locality);
}

function downloadResults(results) {
  const headers = 'locality,prop_type,size_sqft,market_value_low,market_value_mid,market_value_high,rpi,confidence,risk_flags,status\n';
  const rows = results.map(r => {
    if (r.status === 'error') return `${r.locality},${r.prop_type},,,,,,, ${r.error},error`;
    const mv = r.market_value_range || [0, 0];
    return `${r.locality},${r.prop_type},${r.size_sqft},${mv[0]},${r.market_value_mid},${mv[1]},${r.resale_potential_index},${r.confidence_score},${r.risk_flags?.length || 0},success`;
  });
  const csv = headers + rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url;
  a.download = `PropIQ_Batch_${Date.now()}.csv`;
  a.click(); URL.revokeObjectURL(url);
}

export default function BatchUpload({ onViewProperty }) {
  const [properties, setProperties] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const onDrop = useCallback((files) => {
    const file = files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = parseCSV(e.target.result);
        if (parsed.length > 500) {
          setError('File too large. Maximum 500 properties allowed per batch to prevent memory overload.');
          return;
        }
        setProperties(parsed);
        setResults(null);
        setError(null);
      } catch (err) {
        setError('CSV parse error. Check the format.');
      }
    };
    reader.readAsText(file);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'text/csv': ['.csv'] }, maxFiles: 1,
  });

  const downloadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = 'PropIQ_batch_template.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const runBatch = async () => {
    if (!properties.length) return;
    setLoading(true); setProgress(0); setResults(null);
    try {
      // Process in chunks of 10 to show progress
      const allResults = [];
      const chunkSize = 10;
      for (let i = 0; i < properties.length; i += chunkSize) {
        const chunk = properties.slice(i, i + chunkSize);
        const { data } = await axios.post(`${BASE_URL}/api/v1/assess/batch`, chunk,
          { headers: { 'X-API-Key': 'propiq-demo-2026' } });
        allResults.push(...data.results);
        setProgress(Math.round(((i + chunk.length) / properties.length) * 100));
      }
      setResults(allResults);
    } catch (err) {
      setError('Batch assessment failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const successCount = results?.filter(r => r.status === 'success').length || 0;
  const portfolioTotal = results?.reduce((acc, r) => acc + (r.market_value_mid || 0), 0) || 0;

  const chartData = results?.filter(r => r.status === 'success').map((r, i) => ({
    name: `${r.locality} ${r.prop_type?.split('_')[0]}`,
    value: r.market_value_mid,
    rpi: r.resale_potential_index
  })) || [];

  return (
    <div style={{ padding: '0 20px 20px' }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#5F5E5A',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
        Batch Portfolio Assessment
      </div>

      {/* Drop zone */}
      {!properties.length ? (
        <div>
          <div {...getRootProps()} style={{
            border: `2px dashed ${isDragActive ? '#534AB7' : 'rgba(44,44,42,0.18)'}`,
            borderRadius: 10, padding: '24px 16px', textAlign: 'center', cursor: 'pointer',
            background: isDragActive ? '#EEEDFE' : '#F7F6F2',
          }}>
            <input {...getInputProps()} />
            <div style={{ fontSize: 22, marginBottom: 6 }}>📊</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#534AB7', marginBottom: 3 }}>
              Upload CSV file (up to 50 properties)
            </div>
            <div style={{ fontSize: 11, color: '#888780' }}>
              Headers: locality, prop_type, size_sqft, age_years, floor_num, is_freehold, is_rera_registered
            </div>
          </div>
          <button onClick={downloadSample}
            style={{ marginTop: 10, width: '100%', padding: '8px', background: 'none',
              border: '1px solid rgba(44,44,42,0.15)', borderRadius: 8, fontSize: 12,
              color: '#534AB7', cursor: 'pointer', fontFamily: 'Inter, sans-serif' }}>
            ⬇ Download CSV template
          </button>
        </div>
      ) : (
        <div>
          {/* Properties preview */}
          <div style={{ background: '#E1F5EE', border: '1px solid #9FE1CB',
            borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#085041' }}>
              {properties.length} properties loaded
            </div>
            <div style={{ fontSize: 11, color: '#0F6E56', marginTop: 2 }}>
              {[...new Set(properties.map(p => p.locality))].slice(0, 5).join(', ')}
              {properties.length > 5 ? ' ...' : ''}
            </div>
          </div>

          {/* Progress */}
          {loading && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                fontSize: 12, color: '#5F5E5A', marginBottom: 4 }}>
                <span>Processing...</span><span>{progress}%</span>
              </div>
              <div style={{ height: 6, background: '#F1EFE8', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${progress}%`, height: '100%',
                  background: '#534AB7', borderRadius: 3, transition: 'width 0.3s' }} />
              </div>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button onClick={runBatch} disabled={loading}
              style={{ flex: 1, padding: '10px', background: loading ? '#AFA9EC' : '#534AB7',
                color: '#fff', border: 'none', borderRadius: 8, fontSize: 13,
                fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
                fontFamily: 'Inter, sans-serif' }}>
              {loading ? 'Running...' : '⚡ Run Portfolio Re-valuation'}
            </button>
            <button onClick={() => { setProperties([]); setResults(null); }}
              style={{ padding: '10px 14px', background: '#F1EFE8',
                border: '1px solid #D3D1C7', borderRadius: 8, fontSize: 12,
                color: '#444441', cursor: 'pointer', fontFamily: 'Inter, sans-serif' }}>
              Clear
            </button>
          </div>

          {/* Results summary */}
          {results && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
                {[
                  { label: 'Assessed', value: results.length, color: '#534AB7' },
                  { label: 'Success', value: successCount, color: '#0F6E56' },
                  { label: 'Portfolio Val', value: formatINRShort(portfolioTotal).replace('Cr', ' Cr').replace('L', ' L'), color: '#BA7517' },
                ].map(m => (
                  <div key={m.label} style={{ background: '#F7F6F2', borderRadius: 8,
                    padding: '10px 8px', textAlign: 'center' }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: m.color, whiteSpace: 'nowrap' }}>{m.value}</div>
                    <div style={{ fontSize: 10, color: '#888780' }}>{m.label}</div>
                  </div>
                ))}
              </div>

              {/* Visualization */}
              {chartData.length > 0 && (
                <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
                  borderRadius: 10, padding: '12px', marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#5F5E5A', marginBottom: 8, textTransform: 'uppercase' }}>
                    Portfolio Valuation Breakdown
                  </div>
                  <ResponsiveContainer width="100%" height={140}>
                    <BarChart data={chartData} margin={{ left: -20, right: 10, top: 4, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                      <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#888780' }} tickLine={false} axisLine={false} />
                      <YAxis tickFormatter={v => formatINRShort(v)} tick={{ fontSize: 9, fill: '#888780' }} tickLine={false} axisLine={false} />
                      <Tooltip formatter={(val) => [formatINR(val), 'Value']} contentStyle={{ fontSize: 11, borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {chartData.map((d, i) => (
                           <Cell key={i} fill={d.rpi >= 75 ? '#0F6E56' : d.rpi >= 50 ? '#BA7517' : '#A32D2D'} fillOpacity={0.85} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 4, fontSize: 9, color: '#888780' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: 2, background: '#0F6E56' }}/> Highly Liquid</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: 2, background: '#BA7517' }}/> Moderate</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: 2, background: '#A32D2D' }}/> Illiquid</div>
                  </div>
                </div>
              )}

              {/* Results table */}
              <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.10)',
                borderRadius: 10, overflow: 'hidden', marginBottom: 10 }}>
                {results.slice(0, 8).map((r, i) => (
                  <div key={i} onClick={() => r.status === 'success' && onViewProperty && onViewProperty(r)}
                    style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', padding: '8px 12px', cursor: r.status === 'success' ? 'pointer' : 'default',
                    borderBottom: i < results.length - 1 ? '1px solid rgba(44,44,42,0.06)' : 'none',
                    background: i % 2 === 0 ? '#fff' : '#FAFAF8' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 500, color: '#2C2C2A' }}>
                        {r.locality} · {r.prop_type?.replace(/_/g,' ')}
                      </div>
                      {r.status === 'error' && (
                        <div style={{ fontSize: 10, color: '#A32D2D' }}>{r.error}</div>
                      )}
                    </div>
                    {r.status === 'success' && (
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#534AB7' }}>
                          {formatINR(r.market_value_mid)}
                        </div>
                        <div style={{ fontSize: 10, color: '#888780' }}>
                          RPI {r.resale_potential_index?.toFixed(0)}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {results.length > 8 && (
                  <div style={{ padding: '8px 12px', fontSize: 11, color: '#888780',
                    background: '#F7F6F2', textAlign: 'center' }}>
                    +{results.length - 8} more — download CSV for full results
                  </div>
                )}
              </div>

              <button onClick={() => downloadResults(results)}
                style={{ width: '100%', padding: '9px', background: '#0F6E56',
                  color: '#fff', border: 'none', borderRadius: 8, fontSize: 12,
                  fontWeight: 600, cursor: 'pointer', fontFamily: 'Inter, sans-serif' }}>
                ⬇ Download Full Results CSV
              </button>
            </div>
          )}
        </div>
      )}
      {error && (
        <div style={{ background: '#FCEBEB', border: '1px solid #F09595',
          borderRadius: 8, padding: '10px 14px', marginTop: 10,
          fontSize: 12, color: '#791F1F' }}>{error}</div>
      )}
    </div>
  );
}