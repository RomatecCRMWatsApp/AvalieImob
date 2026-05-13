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
  sendEmail: (id, data) => api.post(`/ptam/${id}/email`, data).then(r => r.data),
  // Versionamento
  listVersoes: (id) => api.get(`/ptam/${id}/versoes`).then(r => r.data),
  lacrarVersao: (id, observacao) => api.post(`/ptam/${id}/lacrar`, { observacao }).then(r => r.data),
  getVersao: (id, vid) => api.get(`/ptam/${id}/versoes/${vid}`).then(r => r.data),
  verificarIntegridade: (id, vid) => api.get(`/ptam/${id}/verificar/${vid}`).then(r => r.data),
  // Compartilhamento público
  compartilhar: (id) => api.post(`/ptam/${id}/compartilhar`).then(r => r.data),
  desativarCompartilhamento: (id) => api.delete(`/ptam/${id}/compartilhar`).then(r => r.data),
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
  downloadPdf: (id) => api.get(`/locacao/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  downloadDocx: (id) => api.get(`/locacao/${id}/docx`, { responseType: 'blob' }).then(r => r.data),
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

// ---- SIGEF / INCRA (Consulta automatica para laudos rurais)
export const sigefAPI = {
  consultar: (body) => api.post('/sigef/consultar', body).then(r => r.data),
  importarArquivo: (file, ptamId) => {
    const formData = new FormData();
    formData.append('file', file);
    const params = ptamId ? `?ptam_id=${encodeURIComponent(ptamId)}` : '';
    return api.post(`/sigef/importar-arquivo${params}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  vincular: (ptamId, body) => api.post(`/sigef/vincular-ptam/${ptamId}`, body).then(r => r.data),
  validarCcir: (ccir) => api.get(`/sigef/validar-ccir/${encodeURIComponent(ccir)}`).then(r => r.data),
  moduloFiscal: (municipio, uf, areaHa) => api.get('/sigef/modulo-fiscal', {
    params: { municipio, uf, ...(areaHa != null ? { area_ha: areaHa } : {}) },
  }).then(r => r.data),
  // legacy alias
  vincularPtam: (ptamId, body) => api.post(`/sigef/vincular-ptam/${ptamId}`, body).then(r => r.data),
};

// ---- CND (Certidões Negativas de Débito)
export const cndAPI = {
  consultar: (body) => api.post('/cnd/consultar', body).then(r => r.data),
  getConsulta: (id) => api.get(`/cnd/consulta/${id}`).then(r => r.data),
  getHistorico: () => api.get('/cnd/historico').then(r => r.data),
  deleteConsulta: (id) => api.delete(`/cnd/consulta/${id}`).then(r => r.data),
  downloadCertidao: (id, provider) => api.get(`/cnd/consulta/${id}/download/${provider}`).then(r => r.data),
  anexarPtam: (consultaId, ptamId) => api.post(`/cnd/consulta/${consultaId}/anexar`, { ptam_id: ptamId }).then(r => r.data),
  getConsultasPtam: (ptamId) => api.get('/cnd/historico').then(r => r.data.filter(c => c.ptam_id === ptamId)),
};

// ---- Assinatura Digital D4Sign + ICP-Brasil PAdES
export const assinaturaAPI = {
  // D4Sign (assinatura eletrônica via e-mail)
  iniciar: (tipo, id, payload) => api.post(`/assinatura/${tipo}/${id}/iniciar`, payload),
  status: (tipo, id) => api.get(`/assinatura/${tipo}/${id}/status`),
  download: (tipo, id) => api.get(`/assinatura/${tipo}/${id}/download`, { responseType: 'blob' }),
  cancelar: (tipo, id) => api.delete(`/assinatura/${tipo}/${id}/cancelar`),
  // ICP-Brasil A1/PAdES (certificado .pfx local)
  assinarIcp: (tipo, id, certId) =>
    api.post(`/assinatura/icp/${tipo}/${id}/assinar`, { cert_id: certId }).then(r => r.data),
  downloadIcp: (tipo, id) =>
    api.get(`/assinatura/icp/${tipo}/${id}/download`, { responseType: 'blob' }).then(r => r.data),
  verificarPublico: (hash) =>
    api.get(`/assinatura/v/laudo/v/${hash}`).then(r => r.data),
};

// ---- Certificados Digitais ICP-Brasil A1 (.pfx) — por usuário
export const certificadosAPI = {
  list: () => api.get('/certificados').then(r => r.data),
  upload: (file, { label, perfil, senha }) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    fd.append('label', label);
    fd.append('perfil', perfil);
    fd.append('senha', senha);
    return api.post('/certificados', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  toggle: (id, ativo) => api.patch(`/certificados/${id}/ativar`, { ativo }).then(r => r.data),
  remove: (id) => api.delete(`/certificados/${id}`).then(r => r.data),
};

// ---- PTAM extras: Clonar, Recibo de honorários, WhatsApp via Z-API, Telegram
export const ptamExtrasAPI = {
  clonar: (id) => api.post(`/ptam/${id}/clonar`).then(r => r.data),
  gerarRecibo: (id, payload) => api.post(`/ptam/${id}/recibo`, payload).then(r => r.data),
  downloadRecibo: (id) =>
    api.get(`/ptam/${id}/recibo`, { responseType: 'blob' }).then(r => r.data),
  // chat_id pode vir vazio — backend usa o default das integrações do usuário
  enviarTelegram: (id, chatId = '', legenda = '') =>
    api.post(`/ptam/${id}/telegram`, { chat_id: chatId, legenda }).then(r => r.data),
  // phone com DDI+DDD (Z-API normaliza)
  enviarWhatsApp: (id, phone, legenda = '') =>
    api.post(`/ptam/${id}/whatsapp`, { phone, legenda }).then(r => r.data),
};

// ---- Integrações por usuário (Z-API + Meta WhatsApp + Telegram)
export const integracoesAPI = {
  get: () => api.get('/integracoes').then(r => r.data),
  update: (data) => api.put('/integracoes', data).then(r => r.data),
  // Testes de conexão (validam credenciais sem enviar mensagem real)
  testarZapi: () => api.post('/integracoes/zapi/testar').then(r => r.data),
  testarMeta: () => api.post('/integracoes/meta/testar').then(r => r.data),
  // Envio de mensagem de teste real
  enviarTesteWhatsApp: (phone, mensagem) =>
    api.post('/integracoes/whatsapp/enviar-teste', { phone, mensagem }).then(r => r.data),
  testarTelegram: (chatId, mensagem) =>
    api.post('/integracoes/telegram/testar', { chat_id: chatId, mensagem }).then(r => r.data),
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
  exportPdf: (id) => api.post(`/tvi/vistoria/${id}/export/pdf`, {}, { responseType: 'blob' }).then(r => r.data),
  exportDocx: (id) => api.post(`/tvi/vistoria/${id}/export/docx`, {}, { responseType: 'blob' }).then(r => r.data),
};

// ---- Zonas do Plano Diretor (personalizadas por usuário)
export const zonasAPI = {
  listar: () => api.get('/zonas').then(r => r.data),
  criar: (data) => api.post('/zonas', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/zonas/${id}`, data).then(r => r.data),
  excluir: (id) => api.delete(`/zonas/${id}`).then(r => r.data),
};

// ---- Contratos (compra/venda, locação, permuta, arras, etc.)
const normalizeContrato = (contrato) => {
  if (!contrato) return contrato;
  return {
    ...contrato,
    id: contrato.id || contrato._id || null,
    numero_contrato: contrato.numero_contrato || contrato.numero || '',
    tipo_contrato: contrato.tipo_contrato || contrato.tipo || '',
    vendedores: Array.isArray(contrato.vendedores) ? contrato.vendedores : [],
    compradores: Array.isArray(contrato.compradores) ? contrato.compradores : [],
  };
};

export const contratosAPI = {
  listar: (params) => api.get('/contratos', { params }).then(r => (r.data || []).map(normalizeContrato)),
  criar: (data) => api.post('/contratos', data).then(r => normalizeContrato(r.data)),
  buscar: (id) => api.get(`/contratos/${id}`).then(r => normalizeContrato(r.data)),
  atualizar: (id, data) => api.put(`/contratos/${id}`, data).then(r => normalizeContrato(r.data)),
  excluir: (id) => api.delete(`/contratos/${id}`).then(r => r.data),
};

// ---- Recibos (independentes — honorários, serviços, mão de obra...)
export const recibosAPI = {
  listar: (params) => api.get('/recibos', { params }).then(r => r.data),
  buscar: (id) => api.get(`/recibos/${id}`).then(r => r.data),
  criar: (data) => api.post('/recibos', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/recibos/${id}`, data).then(r => r.data),
  excluir: (id) => api.delete(`/recibos/${id}`).then(r => r.data),
  emitir: (id) => api.post(`/recibos/${id}/emitir`).then(r => r.data),
  // Live preview — body é o estado atual do form
  preview: (data) =>
    api.post('/recibos/preview', data, { responseType: 'blob' }).then(r => r.data),
  // Download PDF do recibo já salvo
  pdf: (id) => api.get(`/recibos/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  // Envio
  enviarWhatsApp: (id, phone = '', legenda = '') =>
    api.post(`/recibos/${id}/enviar-whatsapp`, { phone, legenda }).then(r => r.data),
  // Tipos disponíveis (drives o select)
  tipos: () => api.get('/recibos/tipos').then(r => r.data),
};
