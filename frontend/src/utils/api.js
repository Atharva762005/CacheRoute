// PropIQ API Client v2 — 3 cities, all endpoints, multi-image support
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEMO_KEY = 'propiq-demo-2026';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 300000, // Increased to 5 mins for Render Free Tier ML init
  headers: { 'Content-Type': 'application/json', 'X-API-Key': DEMO_KEY },
});

// ── Core Assessment ────────────────────────────────────────────────────────
export const assessProperty = async (formData) => {
  const { data } = await api.post('/api/v1/assess', formData);
  return data;
};

export const assessFull = async (formData) => {
  const { data } = await api.post('/api/v1/assess/full', formData);
  return data;
};

/**
 * Multi-image assessment.
 * images: Array of { file: File, tag: 'exterior'|'interior' }
 */
export const assessWithImages = async (formData, images = []) => {
  const fd = new FormData();
  Object.entries(formData).forEach(([k, v]) => fd.append(k, v));

  if (images.length === 1) {
    // Keep backward-compat single field
    fd.append('image', images[0].file);
  } else {
    images.forEach((img, i) => {
      fd.append('images', img.file);
      fd.append(`image_tag_${i}`, img.tag || 'exterior');
    });
  }

  const { data } = await axios.post(`${BASE_URL}/api/v1/assess/image`, fd, {
    headers: { 'Content-Type': 'multipart/form-data', 'X-API-Key': DEMO_KEY },
    timeout: 300000, // 5 mins allowed for CLIP image processing on free tier
  });
  return data;
};

// Legacy single-image compat
export const assessWithImage = async (formData, imageFile) =>
  assessWithImages(formData, [{ file: imageFile, tag: 'exterior' }]);

export const downloadPDF = async (formData) => {
  const { data } = await api.post('/api/v1/assess/pdf', formData, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `PropIQ_Report_${formData.locality}_${Date.now()}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const getNarration = async (formData) => {
  const { data } = await api.post('/api/v1/assess/narrate', formData);
  return data;
};

// ── Reference Data ─────────────────────────────────────────────────────────
export const getLocalities = async (city) => {
  const { data } = await api.get('/api/v1/localities', { params: city ? { city } : {} });
  return data;
};

export const getComps = async (locality, propType, sizeSqft, ageYears) => {
  const { data } = await api.get('/api/v1/comps', {
    params: { locality, prop_type: propType, size_sqft: sizeSqft, age_years: ageYears, n: 5 },
  });
  return data;
};

export const getTrend = async (locality, propType) => {
  const { data } = await api.get(`/api/v1/trends/${encodeURIComponent(locality)}`,
    { params: { prop_type: propType } });
  return data;
};

export const getAuditLog = async () => {
  const { data } = await api.get('/api/v1/audit/recent', { params: { limit: 10 } });
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/api/v1/health');
  return data;
};

// ── Formatters ─────────────────────────────────────────────────────────────
export const formatINR = (value) => {
  if (!value && value !== 0) return '—';
  if (value >= 10_000_000) return `₹${(value / 10_000_000).toFixed(2)} Cr`;
  if (value >= 100_000)    return `₹${(value / 100_000).toFixed(2)} L`;
  return `₹${value.toLocaleString('en-IN')}`;
};

export const formatINRShort = (value) => {
  if (!value && value !== 0) return '—';
  if (value >= 10_000_000) return `₹${(value / 10_000_000).toFixed(1)}Cr`;
  if (value >= 100_000)    return `₹${(value / 100_000).toFixed(1)}L`;
  return `₹${value.toLocaleString('en-IN')}`;
};

// ── Constants ──────────────────────────────────────────────────────────────
export const PROP_TYPES = [
  { value: '1bhk_apartment', label: '1 BHK Apartment' },
  { value: '2bhk_apartment', label: '2 BHK Apartment' },
  { value: '3bhk_apartment', label: '3 BHK Apartment' },
  { value: '4bhk_apartment', label: '4 BHK Apartment' },
  { value: 'villa',          label: 'Villa / Bungalow' },
  { value: 'shop',           label: 'Commercial Shop' },
  { value: 'office',         label: 'Office Space' },
  { value: 'plot',           label: 'Plot / Land' },
];

export const LOCALITIES_BY_CITY = {
  Pune: ['Koregaon Park','Shivajinagar','Baner','Kothrud','Aundh','Viman Nagar',
         'Wakad','Hinjewadi','Hadapsar','Pimpri','Chinchwad','Katraj',
         'Wagholi','Talegaon','Chakan','Ambegaon'],
  Mumbai: ['Bandra West','Worli','Powai','Andheri West','Andheri East',
           'Thane','Navi Mumbai','Dadar','Borivali','Mira Road','Virar','Kharghar'],
  Bangalore: ['Koramangala','Indiranagar','Whitefield','HSR Layout','Electronic City',
              'Marathahalli','Sarjapur Road','Yelahanka','Bannerghatta','Devanahalli','Tumkur Road'],
};

export const ALL_LOCALITIES = Object.values(LOCALITIES_BY_CITY).flat();