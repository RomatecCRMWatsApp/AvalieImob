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

// ---- Branding (white-label por usuário: logo, cores, rodapé)
export const brandingAPI = {
  get: () => api.get('/branding').then((r) => r.data),
  // Preview retorna PNG (ou PDF) como Blob — o componente cria o objectURL.
  preview: () => api.get('/branding/preview', { responseType: 'blob' }).then((r) => r.data),
  uploadLogo: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api
      .post('/branding/logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data);
  },
  deleteLogo: () => api.delete('/branding/logo').then((r) => r.data),
  updateColors: (data) => api.put('/branding/colors', data).then((r) => r.data),
  updateFooter: (data) => api.put('/branding/footer', data).then((r) => r.data),
  updateTypography: (data) => api.put('/branding/typography', data).then((r) => r.data),
  setUseDefault: (value) => api.put('/branding/use-default', { use_default: value }).then((r) => r.data),
  reset: () => api.post('/branding/reset').then((r) => r.data),
};

// ---- Galeria de Fotos própria do AvalieImob (independente; banco do AvalieImob)
export const galeriaAPI = {
  listar: (params = {}) => api.get('/galeria', { params }).then((r) => r.data),
  salvar: (blob, meta = {}) => {
    const fd = new FormData();
    fd.append('file', blob, `galeria_${Date.now()}.jpg`);
    Object.entries(meta).forEach(([k, v]) => fd.append(k, v == null ? '' : String(v)));
    return api.post('/galeria/foto', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data);
  },
  remover: (id) => api.delete(`/galeria/foto/${id}`).then((r) => r.data),
  enviarWhatsApp: (id, phone) => api.post(`/galeria/foto/${id}/whatsapp`, { phone }).then((r) => r.data),
  enviarTelegram: (id, chatId = '') => api.post(`/galeria/foto/${id}/telegram`, { chat_id: chatId }).then((r) => r.data),
};

// ---- ZAYRA (Feature 04: importar fotos de campo da Galeria ZAYRA)
export const zayraAPI = {
  galeria: (params = {}) => api.get('/zayra/galeria', { params }).then((r) => r.data),
  importar: (ptamId, fotos) =>
    api.post(`/zayra/importar/${ptamId}`, { fotos }).then((r) => r.data),
  // Preview autenticado (Bearer) — retorna Blob; o componente cria o objectURL.
  // É privado: o backend só serve a foto do avaliador logado.
  preview: (id) =>
    api.get(`/zayra/foto-preview/${id}`, { responseType: 'blob' }).then((r) => r.data),
};

// ---- Conformidade COFECI/CNAI (Feature 05)
export const conformidadeAPI = {
  dashboard: () => api.get('/conformidade/dashboard').then((r) => r.data),
  listarAlertas: (naoLidos = false) =>
    api.get('/conformidade/alertas', { params: { nao_lidos: naoLidos } }).then((r) => r.data),
  marcarLido: (id) => api.patch(`/conformidade/alertas/${id}/lido`).then((r) => r.data),
  verificarAgora: () => api.post('/conformidade/verificar-agora').then((r) => r.data),
  listarCredenciais: () => api.get('/conformidade/credenciais').then((r) => r.data),
  criarCredencial: (data) => api.post('/conformidade/credenciais', data).then((r) => r.data),
  atualizarCredencial: (id, data) =>
    api.put(`/conformidade/credenciais/${id}`, data).then((r) => r.data),
  removerCredencial: (id) =>
    api.delete(`/conformidade/credenciais/${id}`).then((r) => r.data),
  obterConfig: () => api.get('/conformidade/config').then((r) => r.data),
  salvarConfig: (data) => api.put('/conformidade/config', data).then((r) => r.data),
};

// ---- Assinatura ICP-Brasil POSICIONADA (arrastar o retângulo)
export const assinaturaPosAPI = {
  // Certificados do usuário (pra escolher o e-CPF/e-CNPJ)
  certificados: () => api.get('/certificados').then((r) => r.data),
  // Gera o PDF, guarda no R2 e devolve as páginas renderizadas (base64 + dims em pontos)
  preparar: (tipo, id) =>
    api.post(`/assinatura/icp/${tipo}/${id}/preparar`, { layout: 'v2' }).then((r) => r.data),
  // Assina na posição escolhida (coords em PONTOS PDF, origem bottom-left)
  assinar: (tipo, id, body) =>
    api.post(`/assinatura/icp/${tipo}/${id}/posicionado`, body).then((r) => r.data),
};

// ---- INCRA (tabelas de valores de terra nua — imóveis rurais)
export const incraAPI = {
  tabelaVigente: (params = {}) =>
    api.get('/incra/tabela-vigente', { params }).then((r) => r.data),
  listar: () => api.get('/incra/tabelas').then((r) => r.data),
  buscar: (id) => api.get(`/incra/tabela/${id}`).then((r) => r.data),
  criar: (data) => api.post('/incra/tabela', data).then((r) => r.data),
  editar: (id, data) => api.put(`/incra/tabela/${id}`, data).then((r) => r.data),
  remover: (id) => api.delete(`/incra/tabela/${id}`).then((r) => r.data),
  seedExemplo: () => api.post('/incra/seed-exemplo').then((r) => r.data),
  // Vincula uma tabela ao PTAM e congela o snapshot (server-side)
  vincularPtam: (ptamId, body) =>
    api.patch(`/ptam/${ptamId}/tabela-incra`, body).then((r) => r.data),
};

// ---- Clients
export const clientsAPI = {
  list: () => api.get('/clients').then(r => r.data),
  create: (data) => api.post('/clients', data).then(r => r.data),
  update: (id, data) => api.put(`/clients/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/clients/${id}`).then(r => r.data),
  importarPtam: () => api.post('/clients/importar-ptam').then(r => r.data),
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

// ---- Amostras de Mercado v2 (Banco Global de Paradigmas)
export const amostrasAPI = {
  list: (params = {}) => api.get('/amostras-mercado', { params }).then(r => r.data),
  get: (id) => api.get(`/amostras-mercado/${id}`).then(r => r.data),
  create: (data) => api.post('/amostras-mercado', data).then(r => r.data),
  update: (id, data) => api.put(`/amostras-mercado/${id}`, data).then(r => r.data),
  remove: (id) => api.delete(`/amostras-mercado/${id}`).then(r => r.data),
  estatisticas: (params = {}) => api.get('/amostras-mercado/estatisticas', { params }).then(r => r.data),
  proximaReferencia: (categoria = 'urbano') =>
    api.get('/amostras-mercado/meta/proxima-referencia', { params: { categoria } }).then(r => r.data),
  syncPtam: (ptamId) => api.post(`/amostras-mercado/sync/ptam/${ptamId}`).then(r => r.data),
  dedupe: () => api.post('/amostras-mercado/dedupe').then(r => r.data),
};

// ---- Cupons Promocionais (Kit de Captação — admin)
export const cuponsAPI = {
  list: (params = {}) => api.get('/cupons', { params }).then(r => r.data),
  estatisticas: () => api.get('/cupons/estatisticas').then(r => r.data),
  criar: (data) => api.post('/cupons', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/cupons/${id}`, data).then(r => r.data),
  revalidar: (id, payload = {}) => api.put(`/cupons/${id}/revalidar`, payload).then(r => r.data),
  excluir: (id) => api.delete(`/cupons/${id}`).then(r => r.data),
  cancelar: (id) => api.put(`/cupons/${id}/cancelar`).then(r => r.data),
  enviarWhatsApp: (id, payload = {}) => api.post(`/cupons/${id}/enviar-whatsapp`, payload).then(r => r.data),
  // Públicos (página de cadastro)
  validarPublico: (slug) => api.get(`/cupons/publico/validar/${encodeURIComponent(slug)}`).then(r => r.data),
  resgatarPublico: (slug, usuarioId) => api.post(`/cupons/publico/resgatar/${encodeURIComponent(slug)}`, { usuario_id: usuarioId }).then(r => r.data),
};

// ---- Propostas de Consultoria (motor de cálculo port da ZAYRA)
export const propostasAPI = {
  catalogo: () => api.get('/propostas/catalogo').then(r => r.data),
  preview: (subtipo, dados_imovel) => api.post('/propostas/preview', { subtipo, dados_imovel }).then(r => r.data),
  criar: (data) => api.post('/propostas', data).then(r => r.data),
  listar: (params = {}) => api.get('/propostas', { params }).then(r => r.data),
  get: (id) => api.get(`/propostas/${id}`).then(r => r.data),
  atualizar: (id, data) => api.put(`/propostas/${id}`, data).then(r => r.data),
  excluir: (id) => api.delete(`/propostas/${id}`).then(r => r.data),
  pdf: (id) => api.get(`/propostas/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  previewPdf: (subtipo, dados_imovel) =>
    api.post('/propostas/preview/pdf', { subtipo, dados_imovel }, { responseType: 'blob' }).then(r => r.data),
  enviar: (id, data = {}) => api.post(`/propostas/${id}/enviar`, data).then(r => r.data),
};

// ---- Contrato de Exclusividade com aceite eletrônico via WhatsApp ----
export const contratosExclusividadeAPI = {
  // Autenticadas (corretor)
  listar: () => api.get('/contratos-exclusividade').then(r => r.data),
  buscar: (id) => api.get(`/contratos-exclusividade/${id}`).then(r => r.data),
  criar: (data) => api.post('/contratos-exclusividade', data).then(r => r.data),
  criarRascunho: () => api.post('/contratos-exclusividade/rascunho').then(r => r.data),
  atualizar: (id, data) => api.put(`/contratos-exclusividade/${id}`, data).then(r => r.data),
  concluirEtapa: (id, n) => api.post(`/contratos-exclusividade/${id}/etapas/${n}/concluir`).then(r => r.data),
  enviar: (id) => api.post(`/contratos-exclusividade/${id}/enviar`).then(r => r.data),
  reenviar: (id, papel) => api.post(`/contratos-exclusividade/${id}/reenviar/${papel}`).then(r => r.data),
  cancelar: (id) => api.post(`/contratos-exclusividade/${id}/cancelar`).then(r => r.data),
  // Públicas (sem auth)
  obterPorToken: (token) => api.get(`/publico/contratos-exclusividade/aceite/${token}`).then(r => r.data),
  confirmarAceite: (token, body) => api.post(`/publico/contratos-exclusividade/aceite/${token}/confirmar`, body).then(r => r.data),
  verificar: (hash) => api.get(`/publico/contratos-exclusividade/verificar/${hash}`).then(r => r.data),
};

// ---- Assinatura DESENHADA do cliente via WhatsApp (contrato)
export const assinaturaClienteAPI = {
  // Autenticadas (corretor)
  preparar: (cid) => api.post(`/assinatura-cliente/contratos/${cid}/preparar`).then(r => r.data),
  posicionar: (cid, body) => api.post(`/assinatura-cliente/contratos/${cid}/posicionar`, body).then(r => r.data),
  sessao: (cid) => api.get(`/assinatura-cliente/contratos/${cid}/sessao`).then(r => r.data),
  reenviar: (cid, body) => api.post(`/assinatura-cliente/contratos/${cid}/reenviar`, body || {}).then(r => r.data),
  enviarMinuta: (cid, body) => api.post(`/assinatura-cliente/contratos/${cid}/minuta/enviar`, body || {}).then(r => r.data),
  statusAssinado: (cid) => api.get(`/assinatura-cliente/contratos/${cid}/assinado/status`).then(r => r.data),
  reenviarAssinado: (cid, body) => api.post(`/assinatura-cliente/contratos/${cid}/assinado/reenviar`, body || {}).then(r => r.data),
  pdfAssinadoProc: (cid) => api.get(`/assinatura/icp/procuracao/${cid}/download`, { params: { layout: 'v2' }, responseType: 'blob' }).then(r => r.data),
  // Públicas (sem auth)
  obter: (token) => api.get(`/publico/assinatura-cliente/${token}`).then(r => r.data),
  assinar: (token, body) => api.post(`/publico/assinatura-cliente/${token}`, body).then(r => r.data),
};

// ---- Admin (usuários cadastrados / assinaturas) — somente admin/owner/ceo
export const adminAPI = {
  listUsers: () => api.get('/admin/users').then(r => r.data),
  createTestUser: (data) => api.post('/admin/create-test-user', data).then(r => r.data),
  excluirUsuario: (id) => api.delete(`/admin/users/${id}`).then(r => r.data),
  excluirInativos: () => api.post('/admin/users/excluir-inativos').then(r => r.data),
  // Leads da Calculadora pública
  listLeads: (params = {}) => api.get('/admin/leads', { params }).then(r => r.data),
  leadsStats: () => api.get('/admin/leads/stats').then(r => r.data),
  atualizarLead: (id, data) => api.patch(`/admin/leads/${id}`, data).then(r => r.data),
  excluirLead: (id) => api.delete(`/admin/leads/${id}`).then(r => r.data),
  // Base R$/m² da Calculadora — calibração pelos PTAMs reais
  baseM2Stats: () => api.get('/avaliacao-publica/base-stats').then(r => r.data),
  recalibrarBaseM2: () => api.post('/avaliacao-publica/recalibrar-base').then(r => r.data),
  // DANFSe (NFS-e) — preview dos 3 temas (blob PDF)
  danfseExemplo: (tema = 'prime1') => api.get('/nfse/danfse/exemplo', { params: { tema }, responseType: 'blob' }).then(r => r.data),
  danfsePreview: (doc, tema = 'prime1') => api.post('/nfse/danfse/preview', doc, { params: { tema }, responseType: 'blob' }).then(r => r.data),
  // Emissão NFS-e — config por município, teste de certificado, preview da DPS (XML)
  nfseConfigList: () => api.get('/nfse/config').then(r => r.data),
  nfseConfigCreate: (body) => api.post('/nfse/config', body).then(r => r.data),
  nfseConfigUpdate: (id, body) => api.put(`/nfse/config/${id}`, body).then(r => r.data),
  nfseTestarCert: (id) => api.post(`/nfse/config/${id}/testar-cert`).then(r => r.data),
  nfseDpsPreview: (body) => api.post('/nfse/dps/preview', body).then(r => r.data),
  nfseAbrasfPreview: (body) => api.post('/nfse/abrasf/preview', body).then(r => r.data),
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
  chat: (session_id, message, persona = 'geral') => api.post('/ai/chat', { session_id, message, persona }).then(r => r.data),
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
  downloadPdfV2: (id) => api.get(`/ptam/${id}/pdf-v2`, { responseType: 'blob' }).then(r => r.data),
  previewPdf: (data) => api.post('/ptam/preview-pdf', data, { responseType: 'blob' }).then(r => r.data),
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
  // Cartão de Regularidade (CRECI) — salva só esses campos sem mexer no resto do perfil
  setCartaoRegularidade: (data) =>
    api.put('/perfil-avaliador/cartao-regularidade', data).then(r => r.data),
  // Certidão de Regularidade (CRECI) — gerada on-line, tem validade
  setCertidaoRegularidade: (data) =>
    api.put('/perfil-avaliador/certidao-regularidade', data).then(r => r.data),
  // Certificado CNAI — miniatura no currículo do PTAM
  setCertificadoCnai: (data) =>
    api.put('/perfil-avaliador/certificado-cnai', data).then(r => r.data),
};

// ---- Testemunhas salvas (autofill no wizard de Contratos)
export const testemunhasAPI = {
  listar: () => api.get('/testemunhas').then(r => r.data),
  salvar: (data) => api.post('/testemunhas', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/testemunhas/${id}`, data).then(r => r.data),
  excluir: (id) => api.delete(`/testemunhas/${id}`).then(r => r.data),
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
  imageMetadata: (imageId) => api.get(`/upload/image/${imageId}/metadata`).then(r => r.data),
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
  assinarIcp: (tipo, id, certId, layouts = ['v2']) =>
    api.post(`/assinatura/icp/${tipo}/${id}/assinar`, { cert_id: certId, layouts }).then(r => r.data),
  downloadIcp: (tipo, id, layout = 'v2') =>
    api.get(`/assinatura/icp/${tipo}/${id}/download`, { params: { layout }, responseType: 'blob' }).then(r => r.data),
  resetarIcp: (tipo, id) =>
    api.post(`/assinatura/icp/${tipo}/${id}/resetar`).then(r => r.data),
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
  // Envia só a MENSAGEM com o link público via Z-API (sem anexar o PDF)
  enviarWhatsAppLink: (id, phone) =>
    api.post(`/ptam/${id}/whatsapp-link`, { phone }).then(r => r.data),
  // Auditoria do link público (envios + visualizações)
  linkEventos: (id) => api.get(`/ptam/${id}/link-eventos`).then(r => r.data),
  // Importação de Vistoria → PTAM (memorial + fotos)
  vistoriasCompativeis: (id) => api.get(`/ptam/${id}/vistorias-compativeis`).then(r => r.data),
  importarVistoria: (id, vistoriaId, body) => api.post(`/ptam/${id}/importar-vistoria/${vistoriaId}`, body).then(r => r.data),
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
  listPhotos: (id) => api.get(`/tvi/vistoria/${id}/photos`).then(r => r.data),
  uploadPhotos: (id, formData) => api.post(`/tvi/vistoria/${id}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data),
  saveSignature: (id, signatureBase64) => api.post(`/tvi/vistoria/${id}/signature`, { signature: signatureBase64 }).then(r => r.data),
  exportPdf: (id) => api.post(`/tvi/vistoria/${id}/export/pdf`, {}, { responseType: 'blob' }).then(r => r.data),
  exportDocx: (id) => api.post(`/tvi/vistoria/${id}/export/docx`, {}, { responseType: 'blob' }).then(r => r.data),
  // Vistoria de Obra para Averbação
  catalogosAverbacao: () => api.get('/tvi/catalogos/averbacao').then(r => r.data),
  gerarRelatorio: (id) => api.post(`/tvi/vistoria/${id}/relatorio`).then(r => r.data),
  gerarMemorial: (id) => api.post(`/tvi/vistoria/${id}/memorial`).then(r => r.data),
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
  // PDF / DOCX (blobs). template opcional: 'prime1' | 'prime2' | 'tradicional'
  pdf: (id, template) => api.get(`/contratos/${id}/pdf`, {
    params: template ? { template } : {}, responseType: 'blob',
  }).then(r => r.data),
  docx: (id) => api.get(`/contratos/${id}/docx`, { responseType: 'blob' }).then(r => r.data),
  procuracaoPdf: (id) => api.get(`/contratos/${id}/procuracao/pdf`, { responseType: 'blob' }).then(r => r.data),
  reciboArrasDocx: (id) => api.get(`/contratos/${id}/recibo-arras/docx`, { responseType: 'blob' }).then(r => r.data),
  reciboArras: (id) => api.get(`/contratos/${id}/recibo-arras/docx`, { responseType: 'blob' }).then(r => r.data),
  lacrar: (id, body = {}) => api.post(`/contratos/${id}/lacrar`, body).then(r => r.data),
  // D4Sign via motor de assinatura compartilhado (tipo 'contrato' já habilitado)
  assinarD4sign: (id, payload) => api.post(`/assinatura/contrato/${id}/iniciar`, payload).then(r => r.data),
  // PDF assinado (motor ICP compartilhado com o PTAM)
  pdfAssinado: (id, layout = 'v2') =>
    api.get(`/assinatura/icp/contrato/${id}/download`, { params: { layout }, responseType: 'blob' }).then(r => r.data),
  // Link público + histórico
  compartilhar: (id) => api.post(`/contratos/${id}/compartilhar`).then(r => r.data),
  linkEventos: (id) => api.get(`/contratos/${id}/link-eventos`).then(r => r.data),
  // Clonar / Zerar assinatura
  clonar: (id) => api.post(`/contratos/${id}/clonar`).then(r => normalizeContrato(r.data)),
  zerarAssinatura: (id) => api.post(`/contratos/${id}/zerar-assinatura`).then(r => r.data),
  // IA jurídica / cálculos do wizard (endpoints já existentes no backend)
  gerarClausulas: (id, body = {}) => api.post(`/contratos/${id}/gerar-clausulas`, body).then(r => r.data),
  validarJuridico: (id) => api.post(`/contratos/${id}/validar-juridico`).then(r => r.data),
  simuladorPenalidades: (id, body = {}) => api.post(`/contratos/${id}/simulador-penalidades`, body).then(r => r.data),
  checklist: (id) => api.get(`/contratos/${id}/checklist`).then(r => r.data),
  clausulasPreview: (id) => api.get(`/contratos/${id}/clausulas-preview`).then(r => r.data),
};

// ---- Assinatura de Documentos (PDF avulso + ICP posicionado, tipo="documento")
export const documentosAPI = {
  listar: () => api.get('/documentos').then(r => r.data),
  obter: (id) => api.get(`/documentos/${id}`).then(r => r.data),
  upload: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    // NÃO fixar Content-Type: o axios/browser precisa setar o boundary do multipart sozinho.
    return api.post('/documentos/upload', fd).then(r => r.data);
  },
  excluir: (id) => api.delete(`/documentos/${id}`).then(r => r.data),
  pdfOriginal: (id) => api.get(`/documentos/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  pdfAssinado: (id, layout = 'v2') => api.get(`/assinatura/icp/documento/${id}/download`, { params: { layout }, responseType: 'blob' }).then(r => r.data),
};

// ---- Perfis de Corretor (autofill "Usar meus dados" no wizard de partes)
export const perfisCorretorAPI = {
  listar: () => api.get('/perfis-corretor').then(r => r.data || []),
  criar: (data) => api.post('/perfis-corretor', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/perfis-corretor/${id}`, data).then(r => r.data),
  marcarPadrao: (id) => api.put(`/perfis-corretor/${id}/padrao`).then(r => r.data),
  excluir: (id) => api.delete(`/perfis-corretor/${id}`).then(r => r.data),
  seedRomario: () => api.post('/perfis-corretor/seed-romario').then(r => r.data || []),
};

// ---- Consulta CNPJ/CPF (Receita Federal — fallback ProspectaBR → CNPJ.ws → ReceitaWS)
export const consultaAPI = {
  cnpj: (cnpj) => api.get(`/consulta/cnpj/${encodeURIComponent(cnpj)}`).then(r => r.data),
  validarCpf: (cpf, dataNascimento) =>
    api.get('/consulta/cpf/validar', {
      params: { cpf, ...(dataNascimento ? { data_nascimento: dataNascimento } : {}) },
    }).then(r => r.data),
  // PDF do resultado da consulta CNPJ (blob para visualizar/baixar)
  pdf: (dados) =>
    api.post('/consulta/cnpj/pdf', { dados }, { responseType: 'blob' }).then(r => r.data),
  whatsapp: (dados, phone, legenda = '') =>
    api.post('/consulta/cnpj/whatsapp', { dados, phone, legenda }).then(r => r.data),
  telegram: (dados, chat_id = '', legenda = '') =>
    api.post('/consulta/cnpj/telegram', { dados, chat_id, legenda }).then(r => r.data),
  // PDF da validação de CPF
  cpfPdf: (dados) =>
    api.post('/consulta/cpf/pdf', { dados }, { responseType: 'blob' }).then(r => r.data),
  cpfWhatsapp: (dados, phone, legenda = '') =>
    api.post('/consulta/cpf/whatsapp', { dados, phone, legenda }).then(r => r.data),
  cpfTelegram: (dados, chat_id = '', legenda = '') =>
    api.post('/consulta/cpf/telegram', { dados, chat_id, legenda }).then(r => r.data),
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
  // Catálogo cascata categoria → serviço
  catalogo: () => api.get('/recibos/catalogo').then(r => r.data),
  // Clonar recibo (cria novo rascunho)
  clonar: (id) => api.post(`/recibos/${id}/clonar`).then(r => r.data),
  // Anexos (até 5; PDF/JPG/PNG/WebP, 10MB)
  adicionarAnexo: (id, file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post(`/recibos/${id}/anexos`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  removerAnexo: (id, anexoId) =>
    api.delete(`/recibos/${id}/anexos/${anexoId}`).then(r => r.data),
};

// Calculadora pública "Quanto vale meu imóvel?" + captura de lead (sem auth)
export const avaliacaoPublicaAPI = {
  estimar: (imovel) => api.post('/avaliacao-publica/estimar', imovel).then((r) => r.data),
  lead: (payload) => api.post('/avaliacao-publica/lead', payload).then((r) => r.data),
};
