import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('romatec_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const PUBLIC_AUTH_ROUTES = ['/auth/login', '/auth/register'];
const SKIP_401_CLEAR = ['/auth/me'];

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || '';

    if (status === 401) {
      const isPublic = PUBLIC_AUTH_ROUTES.some((route) => url.includes(route));
      const skipClear = SKIP_401_CLEAR.some((route) => url.includes(route));
      if (!isPublic && !skipClear) {
        localStorage.removeItem('romatec_token');
        localStorage.removeItem('romatec_user');
      }
    }

    if (status === 403) {
      const detail = err.response?.data?.detail || '';
      if (detail.toLowerCase().includes('assinatura')) {
        window.dispatchEvent(
          new CustomEvent('avalieimob:subscription-required', { detail: { message: detail } })
        );
        if (!window.location.pathname.includes('/assinatura') && !window.location.pathname.includes('/subscription')) {
          window.location.href = '/dashboard/assinatura';
        }
      }
    }

    return Promise.reject(err);
  }
);

// ---- Auth
export const authAPI = {
  register: (data) => api.post('/auth/register', data).then(r => r.data),
  login: (data) => api.post('/auth/login', data).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
  updateMe: (data) => api.put('/auth/me', data).then(r => r.data),
};

// ---- Clients
export const clientsAPI = {
  list: () => api.get('/clients').then(r => r.data),
  create: (data) => api.post('/clients', data).then(r => r.data),
  update: (id, data) => api.put(`/clients/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/clients/${id}`).then(r => r.data),
};

// ---- Properties
export const propertiesAPI = {
  list: (type) => api.get('/properties', { params: type ? { type } : {} }).then(r => r.data),
  create: (data) => api.post('/properties', data).then(r => r.data),
  update: (id, data) => api.put(`/properties/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/properties/${id}`).then(r => r.data),
};

// ---- Samples
export const samplesAPI = {
  list: () => api.get('/samples').then(r => r.data),
  create: (data) => api.post('/samples', data).then(r => r.data),
  remove: (id) => api.delete(`/samples/${id}`).then(r => r.data),
};

// ---- Evaluations
export const evaluationsAPI = {
  list: () => api.get('/evaluations').then(r => r.data),
  create: (data) => api.post('/evaluations', data).then(r => r.data),
  update: (id, data) => api.put(`/evaluations/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/evaluations/${id}`).then(r => r.data),
};

// ---- Dashboard
export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats').then(r => r.data),
};

// ---- AI
export const aiAPI = {
  chat: (session_id, message) => api.post('/ai/chat', { session_id, message }).then(r => r.data),
  history: (session_id) => api.get(`/ai/history/${session_id}`).then(r => r.data),
};

// ---- PTAM
export const ptamAPI = {
  list: () => api.get('/ptam').then(r => r.data),
  get: (id) => api.get(`/ptam/${id}`).then(r => r.data),
  create: (data) => api.post('/ptam', data).then(r => r.data),
  update: (id, data) => api.put(`/ptam/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/ptam/${id}`).then(r => r.data),
  downloadDocx: (id) => api.get(`/ptam/${id}/docx`, { responseType: 'blob' }).then(r => r.data),
  downloadPdf: (id) => api.get(`/ptam/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
};

// ---- Garantias (NBR 14.653 partes 3 e 5)
export const garantiasAPI = {
  list: (params) => api.get('/garantias', { params }).then(r => r.data),
  get: (id) => api.get(`/garantias/${id}`).then(r => r.data),
  create: (data) => api.post('/garantias', data).then(r => r.data),
  update: (id, data) => api.put(`/garantias/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/garantias/${id}`).then(r => r.data),
};

// ---- Locacao (Avaliação de Locação — Lei 8.245/91)
export const locacaoAPI = {
  list: (params) => api.get('/locacao', { params }).then(r => r.data),
  get: (id) => api.get(`/locacao/${id}`).then(r => r.data),
  create: (data) => api.post('/locacao', data).then(r => r.data),
  update: (id, data) => api.put(`/locacao/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/locacao/${id}`).then(r => r.data),
};

// ---- Semoventes (Penhor Rural Bancário)
export const semoventesAPI = {
  list: (params) => api.get('/semoventes', { params }).then(r => r.data),
  get: (id) => api.get(`/semoventes/${id}`).then(r => r.data),
  create: (data) => api.post('/semoventes', data).then(r => r.data),
  update: (id, data) => api.put(`/semoventes/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/semoventes/${id}`).then(r => r.data),
};


// ---- Subscription
export const subAPI = {
  get: () => api.get('/subscription').then(r => r.data),
  change: (plan_id) => api.post('/subscription/change', { plan_id }).then(r => r.data),
};

// ---- Payments (Mercado Pago)
export const paymentsAPI = {
  createPreference: (plan_id) => api.post('/payments/create-preference', { plan_id }).then(r => r.data),
  status: () => api.get('/payments/status').then(r => r.data),
};

// ---- Perfil Avaliador
export const perfilAPI = {
  get: () => api.get('/perfil-avaliador').then(r => r.data),
  update: (data) => api.put('/perfil-avaliador', data).then(r => r.data),
};

// ---- Upload de imagens
export const uploadAPI = {
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  getImageUrl: (imageId) => `${API_BASE}/upload/image/${imageId}`,
  deleteImage: (imageId) => api.delete(`/upload/image/${imageId}`).then(r => r.data),
};

// ---- Imóveis CRM Romatec (público, sem auth)
export const imoveisAPI = {
  list: () => api.get('/imoveis-crm').then(r => r.data),
};

// ---- TVI (Termo de Vistoria de Imóvel)
export const tviAPI = {
  listModels: () => api.get('/tvi/models').then(r => r.data),
  getModel: (id) => api.get(`/tvi/models/${id}`).then(r => r.data),
  list: (params) => api.get('/tvi/vistorias', { params }).then(r => r.data),
  get: (id) => api.get(`/tvi/vistoria/${id}`).then(r => r.data),
  create: (data) => api.post('/tvi/vistoria', data).then(r => r.data),
  update: (id, data) => api.put(`/tvi/vistoria/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/tvi/vistoria/${id}`).then(r => r.data),
  uploadPhotos: (id, formData) => api.post(`/tvi/vistoria/${id}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data),
  saveSignature: (id, signatureBase64) => api.post(`/tvi/vistoria/${id}/signature`, { signature: signatureBase64 }).then(r => r.data),
};
