// PropIQ Geo Utilities — geocode + nearest-locality resolver

/** Haversine distance in km between two [lat,lon] pairs */
function haversine([lat1, lon1], [lat2, lon2]) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** All known locality coordinates (same as PropertyMap) */
export const LOCALITY_COORDS = {
  // Pune
  'Koregaon Park': [18.5362, 73.8938], 'Baner': [18.559, 73.7868],
  'Kothrud': [18.5074, 73.8077], 'Wakad': [18.5975, 73.7614],
  'Hinjewadi': [18.5912, 73.738], 'Hadapsar': [18.5018, 73.926],
  'Wagholi': [18.5617, 73.9757], 'Talegaon': [18.7332, 73.6723],
  'Chakan': [18.7601, 73.8637], 'Shivajinagar': [18.5308, 73.8474],
  'Aundh': [18.5578, 73.8073], 'Viman Nagar': [18.5679, 73.9143],
  'Pimpri': [18.6279, 73.7997], 'Chinchwad': [18.6436, 73.7983],
  'Katraj': [18.4601, 73.8669], 'Ambegaon': [18.4489, 73.8526],
  // Mumbai
  'Bandra West': [19.0596, 72.8295], 'Worli': [19.0176, 72.8149],
  'Powai': [19.1176, 72.906], 'Andheri West': [19.1362, 72.8296],
  'Andheri East': [19.1136, 72.8697], 'Thane': [19.2183, 72.9781],
  'Navi Mumbai': [19.0368, 73.0158], 'Dadar': [19.0178, 72.8478],
  'Borivali': [19.2307, 72.8567], 'Mira Road': [19.2813, 72.8742],
  'Virar': [19.4588, 72.8139], 'Kharghar': [19.0474, 73.0659],
  // Bangalore
  'Koramangala': [12.9352, 77.6245], 'Indiranagar': [12.9719, 77.6412],
  'Whitefield': [12.9698, 77.7499], 'HSR Layout': [12.9116, 77.6389],
  'Electronic City': [12.8399, 77.677], 'Marathahalli': [12.9591, 77.6974],
  'Sarjapur Road': [12.9102, 77.6846], 'Yelahanka': [13.1005, 77.5963],
  'Bannerghatta': [12.8002, 77.5773], 'Devanahalli': [13.2476, 77.7179],
  'Tumkur Road': [13.0358, 77.526],
};

/**
 * Returns the name of the closest known locality to [lat, lon].
 * Also returns the distance in km.
 */
export function findNearestLocality(lat, lon) {
  let best = null;
  let bestDist = Infinity;
  for (const [name, coords] of Object.entries(LOCALITY_COORDS)) {
    const d = haversine([lat, lon], coords);
    if (d < bestDist) { bestDist = d; best = name; }
  }
  return { locality: best, distanceKm: bestDist };
}

/**
 * Geocode a free-text address via Nominatim.
 * Returns { lat, lon, display } or null.
 */
export async function geocodeAddress(address) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(address)}`;
  const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
  const data = await res.json();
  if (!data.length) return null;
  return {
    lat: parseFloat(data[0].lat),
    lon: parseFloat(data[0].lon),
    display: data[0].display_name,
  };
}
