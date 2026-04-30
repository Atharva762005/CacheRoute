// PropIQ PropertyMap Component — with Address / Lat-Long tab modes
import React, { useEffect, useRef, useState, useCallback } from 'react';

const LOCALITY_COORDS = {
  // Pune
  'Koregaon Park': [18.5362, 73.8938], 'Baner': [18.5590, 73.7868],
  'Kothrud': [18.5074, 73.8077], 'Wakad': [18.5975, 73.7614],
  'Hinjewadi': [18.5912, 73.7380], 'Hadapsar': [18.5018, 73.9260],
  'Wagholi': [18.5617, 73.9757], 'Talegaon': [18.7332, 73.6723],
  'Chakan': [18.7601, 73.8637], 'Shivajinagar': [18.5308, 73.8474],
  'Aundh': [18.5578, 73.8073], 'Viman Nagar': [18.5679, 73.9143],
  'Pimpri': [18.6279, 73.7997], 'Chinchwad': [18.6436, 73.7983],
  'Katraj': [18.4601, 73.8669], 'Ambegaon': [18.4489, 73.8526],
  // Mumbai
  'Bandra West': [19.0596, 72.8295], 'Worli': [19.0176, 72.8149],
  'Powai': [19.1176, 72.9060], 'Andheri West': [19.1362, 72.8296],
  'Andheri East': [19.1136, 72.8697], 'Thane': [19.2183, 72.9781],
  'Navi Mumbai': [19.0368, 73.0158], 'Dadar': [19.0178, 72.8478],
  'Borivali': [19.2307, 72.8567], 'Mira Road': [19.2813, 72.8742],
  'Virar': [19.4588, 72.8139], 'Kharghar': [19.0474, 73.0659],
  // Bangalore
  'Koramangala': [12.9352, 77.6245], 'Indiranagar': [12.9719, 77.6412],
  'Whitefield': [12.9698, 77.7499], 'HSR Layout': [12.9116, 77.6389],
  'Electronic City': [12.8399, 77.6770], 'Marathahalli': [12.9591, 77.6974],
  'Sarjapur Road': [12.9102, 77.6846], 'Yelahanka': [13.1005, 77.5963],
  'Bannerghatta': [12.8002, 77.5773], 'Devanahalli': [13.2476, 77.7179],
  'Tumkur Road': [13.0358, 77.5260],
};

const CITY_CENTERS = {
  Pune: [18.5204, 73.8567],
  Mumbai: [19.0760, 72.8777],
  Bangalore: [12.9716, 77.5946],
};

/** Geocode a free-text address via Nominatim */
async function geocodeAddress(address) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(address)}`;
  const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
  const data = await res.json();
  if (data.length === 0) return null;
  return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon), display: data[0].display_name };
}

const inputStyle = {
  width: '100%', padding: '8px 10px', border: '1px solid rgba(44,44,42,0.15)',
  borderRadius: 8, fontSize: 12, color: '#2C2C2A', background: '#fff',
  outline: 'none', fontFamily: 'Inter, sans-serif', boxSizing: 'border-box',
};

export default function PropertyMap({ locality, result, city, onLocationResolved, geo_lat, geo_lon }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

  const [locMode, setLocMode] = useState('address'); // 'address' | 'latlong'
  const [addressInput, setAddressInput] = useState('');
  const [latInput, setLatInput] = useState('');
  const [lngInput, setLngInput] = useState('');
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeError, setGeocodeError] = useState('');
  const [resolvedCoords, setResolvedCoords] = useState(null);

  // Derive coordinates to display — priority: exact user-provided > resolvedCoords > locality lookup > city center
  const defaultCenter = CITY_CENTERS[city] || CITY_CENTERS.Pune;
  let coords;
  if (geo_lat != null && geo_lon != null) {
    // Exact coordinates from user — highest priority, pin right here
    coords = [geo_lat, geo_lon];
  } else if (resolvedCoords) {
    coords = [resolvedCoords.lat, resolvedCoords.lon];
  } else if (locality && LOCALITY_COORDS[locality]) {
    coords = LOCALITY_COORDS[locality];
  } else if (result?.enrichment?.geo?.lat) {
    coords = [result.enrichment.geo.lat, result.enrichment.geo.lon];
  } else {
    coords = defaultCenter;
  }

  // When locality or exact coords change, reset the map's own custom coords
  useEffect(() => {
    // If parent provides exact coords, the map's own inputs are secondary
    if (geo_lat != null && geo_lon != null) {
      setResolvedCoords(null); // clear map-level override; parent coords take priority
    }
    setAddressInput('');
    setLatInput('');
    setLngInput('');
    setGeocodeError('');
  }, [locality, city, geo_lat, geo_lon]);

  // Init map
  useEffect(() => {
    const tryInit = () => {
      if (!mapRef.current || !window.L) return false;
      if (!mapInstanceRef.current) {
        mapInstanceRef.current = window.L.map(mapRef.current, {
          center: coords, zoom: 14, zoomControl: true,
        });
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors',
        }).addTo(mapInstanceRef.current);
      }
      return true;
    };
    if (!tryInit()) {
      const t = setInterval(() => { if (tryInit()) clearInterval(t); }, 300);
      return () => clearInterval(t);
    }
  }, []);

  // Update marker when coords change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.L) return;

    if (markerRef.current) markerRef.current.remove();

    const displayName = resolvedCoords?.display
      || (locality || (city ? `${city} Area` : 'Location'));

    const popupContent = result
      ? `<div style="font-family:Inter,sans-serif;min-width:160px">
          <div style="font-weight:700;font-size:13px;margin-bottom:4px">${displayName}</div>
          <div style="font-size:12px;color:#534AB7;font-weight:600">
            ₹${(result.market_value_mid / 1e5).toFixed(1)}L (mid est.)</div>
          <div style="font-size:11px;color:#888780;margin-top:2px">
            RPI: ${result.resale_potential_index} · Confidence: ${Math.round(result.confidence_score * 100)}%
          </div>
        </div>`
      : `<b style="font-family:Inter,sans-serif;font-size:12px">${displayName}</b>`;

    const icon = window.L.divIcon({
      className: '',
      html: `<div style="width:28px;height:28px;background:#534AB7;border-radius:50% 50% 50% 0;
               transform:rotate(-45deg);border:3px solid #fff;
               box-shadow:0 2px 8px rgba(83,74,183,0.5)"></div>`,
      iconSize: [28, 28], iconAnchor: [14, 28],
    });

    markerRef.current = window.L.marker(coords, { icon })
      .addTo(map)
      .bindPopup(popupContent);

    map.setView(coords, 14);
    if (result) markerRef.current.openPopup();
  }, [coords[0], coords[1], result]);

  // Geocode address
  const handleGeocode = useCallback(async () => {
    const q = addressInput.trim();
    if (!q) return;
    setGeocoding(true);
    setGeocodeError('');
    try {
      const geo = await geocodeAddress(q);
      if (!geo) { setGeocodeError('Address not found. Try a more specific query.'); return; }
      setResolvedCoords(geo);
      if (onLocationResolved) onLocationResolved({ lat: geo.lat, lon: geo.lon, address: geo.display });
    } catch {
      setGeocodeError('Geocoding failed. Check your connection.');
    } finally {
      setGeocoding(false);
    }
  }, [addressInput, onLocationResolved]);

  // Apply lat-long
  const handleLatLng = useCallback(() => {
    const lat = parseFloat(latInput);
    const lon = parseFloat(lngInput);
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setGeocodeError('Enter valid lat (−90 to 90) and lng (−180 to 180).');
      return;
    }
    setGeocodeError('');
    const geo = { lat, lon, display: `${lat.toFixed(5)}, ${lon.toFixed(5)}` };
    setResolvedCoords(geo);
    if (onLocationResolved) onLocationResolved({ lat, lon });
  }, [latInput, lngInput, onLocationResolved]);

  const tabBtn = (active) => ({
    flex: 1, padding: '6px 0', border: 'none',
    background: active ? '#534AB7' : 'transparent',
    color: active ? '#fff' : '#888780',
    fontSize: 11, fontWeight: active ? 600 : 400,
    cursor: 'pointer', fontFamily: 'Inter, sans-serif',
    borderRadius: 6, transition: 'all 0.15s',
  });

  return (
    <div style={{ padding: '0 20px 16px' }}>
      {/* Section label */}
      <div style={{ fontSize: 11, fontWeight: 600, color: '#5F5E5A',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        Property Location
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', background: '#F1EFE8', borderRadius: 8,
        padding: 3, gap: 3, marginBottom: 10 }}>
        <button style={tabBtn(locMode === 'address')} onClick={() => { setLocMode('address'); setGeocodeError(''); }}>
          📍 Address
        </button>
        <button style={tabBtn(locMode === 'latlong')} onClick={() => { setLocMode('latlong'); setGeocodeError(''); }}>
          🎯 Lat-Long
        </button>
      </div>

      {/* Address mode */}
      {locMode === 'address' && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              placeholder="e.g. Koregaon Park, Pune"
              value={addressInput}
              onChange={e => setAddressInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleGeocode()}
            />
            <button
              onClick={handleGeocode}
              disabled={geocoding || !addressInput.trim()}
              style={{
                padding: '8px 12px', border: 'none', borderRadius: 8,
                background: geocoding || !addressInput.trim() ? '#AFA9EC' : '#534AB7',
                color: '#fff', fontSize: 11, fontWeight: 600,
                cursor: geocoding || !addressInput.trim() ? 'not-allowed' : 'pointer',
                fontFamily: 'Inter, sans-serif', whiteSpace: 'nowrap',
              }}
            >
              {geocoding ? '…' : 'Locate'}
            </button>
          </div>
          {resolvedCoords && locMode === 'address' && (
            <div style={{ fontSize: 10, color: '#0F6E56', marginTop: 4, fontWeight: 500 }}>
              ✓ {resolvedCoords.lat.toFixed(4)}, {resolvedCoords.lon.toFixed(4)}
            </div>
          )}
        </div>
      )}

      {/* Lat-Long mode */}
      {locMode === 'latlong' && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              placeholder="Latitude e.g. 18.5362"
              type="number" step="0.0001"
              value={latInput}
              onChange={e => setLatInput(e.target.value)}
            />
            <input
              style={{ ...inputStyle, flex: 1 }}
              placeholder="Longitude e.g. 73.8938"
              type="number" step="0.0001"
              value={lngInput}
              onChange={e => setLngInput(e.target.value)}
            />
            <button
              onClick={handleLatLng}
              disabled={!latInput || !lngInput}
              style={{
                padding: '8px 12px', border: 'none', borderRadius: 8,
                background: !latInput || !lngInput ? '#AFA9EC' : '#534AB7',
                color: '#fff', fontSize: 11, fontWeight: 600,
                cursor: !latInput || !lngInput ? 'not-allowed' : 'pointer',
                fontFamily: 'Inter, sans-serif', whiteSpace: 'nowrap',
              }}
            >
              Pin
            </button>
          </div>
          {resolvedCoords && locMode === 'latlong' && (
            <div style={{ fontSize: 10, color: '#0F6E56', marginTop: 4, fontWeight: 500 }}>
              ✓ Pinned at {resolvedCoords.lat.toFixed(5)}, {resolvedCoords.lon.toFixed(5)}
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {geocodeError && (
        <div style={{ fontSize: 10, color: '#c0392b', background: '#fdecea', borderRadius: 6,
          padding: '4px 8px', marginBottom: 8 }}>
          ⚠ {geocodeError}
        </div>
      )}

      {/* Map canvas */}
      <div ref={mapRef} style={{ height: 180, borderRadius: 10,
        border: '1px solid rgba(44,44,42,0.12)', overflow: 'hidden' }} />

      {/* Coordinates display */}
      <div style={{ fontSize: 10, color: '#888780', marginTop: 4, textAlign: 'right' }}>
        {coords[0].toFixed(4)}, {coords[1].toFixed(4)}
      </div>
    </div>
  );
}