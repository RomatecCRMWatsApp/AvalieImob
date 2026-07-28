import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('romatec_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const PUBLIC_AUTH_ROUTES = ['/auth/login', '/auth/register', '/auth/forgot-password', '/auth/reset-password'];
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
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }).then(r => r.data),
  resetPassword: (token, password) => api.post('/auth/reset-password', { token, password }).then(r => r.data),
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
  // Baixa/visualiza o PDF assinado (ICP) — blob
  downloadIcp: (tipo, id, layout = 'v2') =>
    api.get(`/assinatura/icp/${tipo}/${id}/download`, { params: { layout }, responseType: 'blob' }).then((r) => r.data),
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
  usersAudit: () => api.get('/admin/users/audit').then(r => r.data),
  userTimeline: (id) => api.get(`/admin/users/${id}/timeline`).then(r => r.data),
  createTestUser: (data) => api.post('/admin/create-test-user', data).then(r => r.data),
  emailStatus: () => api.get('/admin/email/status').then(r => r.data),
  emailTest: (to) => api.post('/admin/email/test', { to }).then(r => r.data),
  emailWelcome: (body) => api.post('/admin/email/welcome', body).then(r => r.data),
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
  // DANFSe — importar uma NFS-e JÁ emitida (PDF) → extrai os campos p/ re-tematizar
  danfseImportar: (file) => { const fd = new FormData(); fd.append('file', file); return api.post('/nfse/danfse/importar', fd).then(r => r.data); },
  // DANFSe — envia o PDF tematizado por WhatsApp (Z-API/Meta do usuário)
  danfseEnviarWhatsapp: (doc, tema, telefone, legenda) => api.post('/nfse/danfse/enviar-whatsapp', { doc, telefone, legenda }, { params: { tema } }).then(r => r.data),
  // Emissão NFS-e — config por município, teste de certificado, preview da DPS (XML)
  nfseConfigList: () => api.get('/nfse/config').then(r => r.data),
  nfseConfigCreate: (body) => api.post('/nfse/config', body).then(r => r.data),
  nfseConfigUpdate: (id, body) => api.put(`/nfse/config/${id}`, body).then(r => r.data),
  nfseTestarCert: (id) => api.post(`/nfse/config/${id}/testar-cert`).then(r => r.data),
  nfseDpsPreview: (body) => api.post('/nfse/dps/preview', body).then(r => r.data),
  nfseAbrasfPreview: (body) => api.post('/nfse/abrasf/preview', body).then(r => r.data),
  nfseAbrasfTestar: (body) => api.post('/nfse/abrasf/testar-envio', body).then(r => r.data),
  nfseAbrasfConsultarRps: (body) => api.post('/nfse/abrasf/consultar-rps', body).then(r => r.data),
};

// ---- Prospecção B2B (imobiliárias) + campanhas de e-mail
export const reativacaoAPI = {
  status: () => api.get('/reativacao/status').then(r => r.data),
  salvarConfig: (body) => api.post('/reativacao/config', body).then(r => r.data),
  enviarTeste: (body) => api.post('/reativacao/enviar-teste', body).then(r => r.data),
  rodarAgora: (body) => api.post('/reativacao/rodar-agora', body || {}).then(r => r.data),
  reenviar: (body) => api.post('/reativacao/reenviar', body).then(r => r.data),
};

export const prospeccaoAPI = {
  listar: (params = {}) => api.get('/prospeccao', { params }).then(r => r.data),
  stats: () => api.get('/prospeccao/stats').then(r => r.data),
  seed: () => api.post('/prospeccao/seed').then(r => r.data),
  importar: (prospects) => api.post('/prospeccao/importar', { prospects }).then(r => r.data),
  criar: (body) => api.post('/prospeccao', body).then(r => r.data),
  atualizar: (id, body) => api.patch(`/prospeccao/${id}`, body).then(r => r.data),
  excluir: (id) => api.delete(`/prospeccao/${id}`).then(r => r.data),
  enviarCampanha: (body) => api.post('/prospeccao/campanha/enviar', body).then(r => r.data),
  campanhaStatus: () => api.get('/prospeccao/campanha/status').then(r => r.data),
  pararCampanha: () => api.post('/prospeccao/campanha/parar').then(r => r.data),
  resetErros: () => api.post('/prospeccao/campanha/reset-erros').then(r => r.data),
  propostaPreview: () => api.get('/prospeccao/proposta/preview').then(r => r.data),
  getAuto: () => api.get('/prospeccao/campanha/auto').then(r => r.data),
  setAuto: (body) => api.post('/prospeccao/campanha/auto', body).then(r => r.data),
  // Campanha por WhatsApp (Z-API) — 1 a 2/dia
  waStatus: () => api.get('/prospeccao/whatsapp/status').then(r => r.data),
  waConfigGet: () => api.get('/prospeccao/whatsapp/config').then(r => r.data),
  waConfigSet: (body) => api.post('/prospeccao/whatsapp/config', body).then(r => r.data),
  waEnviar: (body) => api.post('/prospeccao/whatsapp/enviar', body).then(r => r.data),
  waWebhookInfo: () => api.get('/prospeccao/whatsapp/webhook').then(r => r.data),
  waWebhookAtivar: () => api.post('/prospeccao/whatsapp/webhook/ativar').then(r => r.data),
  waWebhookDesativar: () => api.post('/prospeccao/whatsapp/webhook/desativar').then(r => r.data),
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

// ---- Instagram Studio
export const instagramAPI = {
  gerar: (pilar, assunto, formato) =>
    api.post('/instagram/gerar', { pilar, assunto, formato }).then(r => r.data),
  listar: (params = {}) =>
    api.get('/instagram/posts', { params }).then(r => r.data),
  obter: (id) => api.get(`/instagram/posts/${id}`).then(r => r.data),
  criar: (data) => api.post('/instagram/posts', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/instagram/posts/${id}`, data).then(r => r.data),
  status: (id, status) => api.post(`/instagram/posts/${id}/status`, { status }).then(r => r.data),
  excluir: (id) => api.delete(`/instagram/posts/${id}`).then(r => r.data),
  enviarWhatsapp: (id, data) => api.post(`/instagram/posts/${id}/enviar-whatsapp`, data).then(r => r.data),
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
  completude: () => api.get('/perfil-avaliador/completude').then(r => r.data),
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
  // Assinatura gráfica do RT — carimbada no Memorial do Geo Urbano (PNG transparente)
  setAssinaturaTecnico: (assinatura_b64) =>
    api.put('/perfil-avaliador/assinatura-tecnico', { assinatura_b64 }).then(r => r.data),
  setAssinaturaTecnicoPos: (pos) =>
    api.put('/perfil-avaliador/assinatura-tecnico-pos', pos).then(r => r.data),
  setCarimboQualidades: (carimbo_qualidades) =>
    api.put('/perfil-avaliador/carimbo-qualidades', { carimbo_qualidades }).then(r => r.data),
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

// ---- Documentos Externos (doc-ext): upload de PDF arbitrário, N signatários, WhatsApp + ICP
export const documentosExternosAPI = {
  listar: () => api.get('/documentos-externos').then(r => r.data),
  obter: (id) => api.get(`/documentos-externos/${id}`).then(r => r.data),
  upload: (formData) => api.post('/documentos-externos/upload', formData).then(r => r.data),
  editar: (id, body) => api.patch(`/documentos-externos/${id}`, body).then(r => r.data),
  excluir: (id) => api.delete(`/documentos-externos/${id}`).then(r => r.data),
  addSignatario: (id, body) => api.post(`/documentos-externos/${id}/signatarios`, body).then(r => r.data),
  editSignatario: (id, sid, body) => api.patch(`/documentos-externos/${id}/signatarios/${sid}`, body).then(r => r.data),
  delSignatario: (id, sid) => api.delete(`/documentos-externos/${id}/signatarios/${sid}`).then(r => r.data),
  preparar: (id) => api.post(`/documentos-externos/${id}/preparar`).then(r => r.data),
  posicionar: (id, body) => api.post(`/documentos-externos/${id}/posicionar`, body).then(r => r.data),
  reenviar: (id, body) => api.post(`/documentos-externos/${id}/reenviar`, body).then(r => r.data),
  status: (id) => api.get(`/documentos-externos/${id}/sessao-status`).then(r => r.data),
  distribuirFinal: (id, body) => api.post(`/documentos-externos/${id}/distribuir-final`, body || {}).then(r => r.data),
  pdfOriginal: (id) => api.get(`/documentos-externos/${id}/pdf-original`, { responseType: 'blob' }).then(r => r.data),
  pdfFinal: (id) => api.get(`/documentos-externos/${id}/pdf-final`, { responseType: 'blob' }).then(r => r.data),
};

// ---- Documentos Externos — público (sem token JWT) — página de assinatura no celular
export const documentosExternosPublicoAPI = {
  obter: (token) => api.get(`/publico/documentos-externos/${token}`).then(r => r.data),
  assinar: (token, body) => api.post(`/publico/documentos-externos/${token}`, body).then(r => r.data),
  recusar: (token, body) => api.post(`/publico/documentos-externos/${token}/recusar`, body).then(r => r.data),
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

// Topografia & Geo — Georreferenciamento / Requerimentos Cartoriais
const GEOREF = '/topografia/georef';
export const georefAPI = {
  listar: (params = {}) => api.get(`${GEOREF}/projetos`, { params }).then((r) => r.data),
  criar: (data) => api.post(`${GEOREF}/projetos`, data).then((r) => r.data),
  obter: (id) => api.get(`${GEOREF}/projetos/${id}`).then((r) => r.data),
  atualizar: (id, data) => api.patch(`${GEOREF}/projetos/${id}`, data).then((r) => r.data),
  excluir: (id) => api.delete(`${GEOREF}/projetos/${id}`).then((r) => r.data),

  // Upload de documento-fonte (tipo: memorial|mapa|ccir|certidao|doc_cliente).
  // NÃO fixar Content-Type: o axios precisa setar o boundary do multipart sozinho.
  upload: (id, tipo, file) => {
    const fd = new FormData();
    fd.append('tipo', tipo);
    fd.append('file', file);
    return api.post(`${GEOREF}/projetos/${id}/upload`, fd).then((r) => r.data);
  },
  // Remove UM arquivo de um upload multi (ex.: um exercício do ITR)
  removerUploadItem: (id, tipo, itemId) =>
    api.delete(`${GEOREF}/projetos/${id}/uploads/${tipo}/${itemId}`).then((r) => r.data),
  // Status de assinatura ICP de cada peça (persiste — não some ao recarregar)
  listarAssinaturas: (id) =>
    api.get(`${GEOREF}/projetos/${id}/assinaturas`).then((r) => r.data),
  // Parcelas (desmembramento/remembramento)
  adicionarParcela: (id, rotulo) =>
    api.post(`${GEOREF}/projetos/${id}/parcelas`, { rotulo }).then((r) => r.data),
  removerParcela: (id, parcelaId) =>
    api.delete(`${GEOREF}/projetos/${id}/parcelas/${parcelaId}`).then((r) => r.data),
  uploadParcela: (id, parcelaId, tipo, file) => {
    const fd = new FormData();
    fd.append('tipo', tipo);
    fd.append('file', file);
    return api.post(`${GEOREF}/projetos/${id}/parcelas/${parcelaId}/upload`, fd).then((r) => r.data);
  },
  // Memorial de uma parcela específica (blob)
  memorialParcela: (id, parcelaId, fmt = 'pdf', tema) =>
    api.get(`${GEOREF}/projetos/${id}/documentos/memorial`,
      { params: { fmt, parcela: parcelaId, ...(tema ? { tema } : {}) }, responseType: 'blob' })
      .then((r) => r.data),

  extrair: (id) => api.post(`${GEOREF}/projetos/${id}/extrair`).then((r) => r.data),

  // Composição do dossiê (picker de peças + presets)
  composicaoOpcoes: () => api.get(`${GEOREF}/composicao/opcoes`).then((r) => r.data),
  composicaoPreview: (id) =>
    api.get(`${GEOREF}/projetos/${id}/composicao/preview`).then((r) => r.data),
  salvarComposicao: (id, body) =>
    api.post(`${GEOREF}/projetos/${id}/composicao`, body).then((r) => r.data),

  // Cartório pelo CNS (tabela oficial de serventias)
  buscarServentia: (cns) =>
    api.get(`${GEOREF}/serventias`, { params: { cns } }).then((r) => r.data),
  // Prepara uma peça p/ assinatura ICP (retorna {id} usado no assinador tipo="georef")
  prepararAssinatura: (id, body) =>
    api.post(`${GEOREF}/projetos/${id}/assinar`, body).then((r) => r.data),
  previewGeojson: (id) => api.get(`${GEOREF}/projetos/${id}/preview-geojson`).then((r) => r.data),
  validar: (id) => api.get(`${GEOREF}/projetos/${id}/validar`).then((r) => r.data),
  gerar: (id, data = {}) => api.post(`${GEOREF}/projetos/${id}/gerar`, data).then((r) => r.data),
  enviarWhatsapp: (id, body) => api.post(`${GEOREF}/projetos/${id}/enviar-whatsapp`, body).then((r) => r.data),

  // Downloads (blob). `modo` (unificado|separado) só afeta o Laudo/Dossiê em desmembramento.
  documento: (id, tipo, fmt = 'pdf', tema, modo, parcela) =>
    api.get(`${GEOREF}/projetos/${id}/documentos/${tipo}`,
      { params: { fmt, ...(tema ? { tema } : {}), ...(modo ? { modo } : {}), ...(parcela ? { parcela } : {}) },
        responseType: 'blob' }).then((r) => r.data),
  drl: (id, confKey, fmt = 'pdf', tema) =>
    api.get(`${GEOREF}/projetos/${id}/documentos/drl/${encodeURIComponent(confKey)}`,
      { params: { fmt, ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  shapefile: (id) =>
    api.get(`${GEOREF}/projetos/${id}/shapefile`, { responseType: 'blob' }).then((r) => r.data),
  shapefileAtributos: (id) =>
    api.get(`${GEOREF}/projetos/${id}/shapefile/atributos`).then((r) => r.data),
  kml: (id) =>
    api.get(`${GEOREF}/projetos/${id}/kml`, { responseType: 'blob' }).then((r) => r.data),

  // Cancelamento de parcela SIGEF (Ofício Circular 814/2026/INCRA)
  cancelamentoJustificativas: () =>
    api.get(`${GEOREF}/cancelamento/justificativas`).then((r) => r.data),
  cancelamentoChecklist: (id) =>
    api.get(`${GEOREF}/projetos/${id}/cancelamento/checklist`).then((r) => r.data),
  cancelamentoUpload: (id, chave, file) => {
    const fd = new FormData();
    fd.append('chave', chave);
    fd.append('file', file);
    return api.post(`${GEOREF}/projetos/${id}/cancelamento/upload`, fd).then((r) => r.data);
  },
  cancelamentoRemoverAnexo: (id, chave) =>
    api.delete(`${GEOREF}/projetos/${id}/cancelamento/anexo/${encodeURIComponent(chave)}`).then((r) => r.data),
  cancelamentoAnexoBlob: (id, chave, fmt) =>
    api.get(`${GEOREF}/projetos/${id}/cancelamento/anexo/${encodeURIComponent(chave)}`,
      { params: fmt ? { fmt } : {}, responseType: 'blob' }).then((r) => r.data),
  cancelamentoValidarOds: (id) =>
    api.post(`${GEOREF}/projetos/${id}/cancelamento/ods/validar`).then((r) => r.data),
  cancelamentoCorrigirOds: (id) =>
    api.post(`${GEOREF}/projetos/${id}/cancelamento/ods/corrigir`).then((r) => r.data),
  cancelamentoDossie: (id, fmt) =>
    api.get(`${GEOREF}/projetos/${id}/documentos/dossie_cancelamento`,
      { params: fmt ? { fmt } : {}, responseType: 'blob' }).then((r) => r.data),
};

// Topografia & Geo — Geo Urbano (Remembramento e demais serviços urbanos)
const GEOURB = '/topografia/geo-urbano';
export const geoUrbanoAPI = {
  listar: (params = {}) => api.get(`${GEOURB}/projetos`, { params }).then((r) => r.data),
  criar: (data) => api.post(`${GEOURB}/projetos`, data).then((r) => r.data),
  criarSeed: () => api.post(`${GEOURB}/projetos/seed`).then((r) => r.data),
  obter: (id) => api.get(`${GEOURB}/projetos/${id}`).then((r) => r.data),
  atualizar: (id, data) => api.patch(`${GEOURB}/projetos/${id}`, data).then((r) => r.data),
  excluir: (id) => api.delete(`${GEOURB}/projetos/${id}`).then((r) => r.data),
  // Upload de documento-fonte (mapas/BCI/certidões/IPTU/proprietário/TRT).
  // NÃO fixar Content-Type: o axios precisa setar o boundary do multipart sozinho.
  upload: (id, tipo, file, vinculo = {}) => {
    const fd = new FormData();
    fd.append('tipo', tipo);
    fd.append('file', file);
    if (vinculo.matricula_id) fd.append('matricula_id', vinculo.matricula_id);
    if (vinculo.parte_id) fd.append('parte_id', vinculo.parte_id);
    return api.post(`${GEOURB}/projetos/${id}/upload`, fd).then((r) => r.data);
  },
  removerUpload: (id, tipo, itemId) =>
    api.delete(`${GEOURB}/projetos/${id}/uploads/${tipo}/${itemId}`).then((r) => r.data),
  extrair: (id) => api.post(`${GEOURB}/projetos/${id}/extrair`).then((r) => r.data),
  reconciliacao: (id) => api.get(`${GEOURB}/projetos/${id}/reconciliacao`).then((r) => r.data),
  previewGeojson: (id) => api.get(`${GEOURB}/projetos/${id}/preview-geojson`).then((r) => r.data),
  gerar: (id, data = {}) => api.post(`${GEOURB}/projetos/${id}/gerar`, data).then((r) => r.data),
  documento: (id, tipo, tema, lote) =>
    api.get(`${GEOURB}/projetos/${id}/documentos/${tipo}`,
      { params: { ...(tema ? { tema } : {}), ...(lote ? { lote } : {}) }, responseType: 'blob' }).then((r) => r.data),
  conservacaoArea: (id) => api.get(`${GEOURB}/projetos/${id}/conservacao-area`).then((r) => r.data),
  // SIG-RI (Prov. CNJ 195/2025) — malha fundiária do RI
  shapefile: (id) => api.get(`${GEOURB}/projetos/${id}/shapefile`, { responseType: 'blob' }).then((r) => r.data),
  kml: (id) => api.get(`${GEOURB}/projetos/${id}/kml`, { responseType: 'blob' }).then((r) => r.data),
  geojson: (id) => api.get(`${GEOURB}/projetos/${id}/geojson`).then((r) => r.data),
  // Painel de validação SIG-RI/ONR (§7) — E-*/W-* + pode_gerar
  validarOnr: (id) => api.post(`${GEOURB}/projetos/${id}/onr/validar`).then((r) => r.data),
  justificarOnr: (id, codigo, texto) =>
    api.post(`${GEOURB}/projetos/${id}/onr/justificar`, { codigo, texto }).then((r) => r.data),
  retificacaoAnalise: (id) => api.get(`${GEOURB}/projetos/${id}/retificacao/analise`).then((r) => r.data),
  retificacaoConfirmar: (id) => api.post(`${GEOURB}/projetos/${id}/retificacao/confirmar`).then((r) => r.data),
  // Orientação dos lados do lote (frente/laterais/fundo); frenteIdx opcional força a testada
  orientar: (id, frenteIdx) => api.post(`${GEOURB}/projetos/${id}/orientar`,
    null, { params: frenteIdx == null ? {} : { frente_idx: frenteIdx } }).then((r) => r.data),
  // DRL — anuência dos confrontantes (eixo geométrico)
  listarDrls: (id) => api.get(`${GEOURB}/projetos/${id}/drls`).then((r) => r.data),
  baixarDrl: (id, cid, tema) =>
    api.get(`${GEOURB}/projetos/${id}/drl/${cid}`, { params: { ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  drlAnuencia: (id, cid, status) => api.post(`${GEOURB}/projetos/${id}/drl/${cid}/anuencia`, { status }).then((r) => r.data),
  // Aprovação & assinaturas (Addendum)
  aprovacaoStatus: (id) => api.get(`${GEOURB}/projetos/${id}/aprovacao/status`).then((r) => r.data),
  aprovacaoEnviar: (id) => api.post(`${GEOURB}/projetos/${id}/aprovacao/enviar`).then((r) => r.data),
  aprovacaoSuperintendencia: (id, body) =>
    api.post(`${GEOURB}/projetos/${id}/aprovacao/superintendencia`, body).then((r) => r.data),
  gerarOficio: (id) => api.post(`${GEOURB}/projetos/${id}/gerar/oficio`).then((r) => r.data),
  // Assinatura ICP do técnico (Memorial/Mapa) — abre o assinador tipo="geo_urbano"
  prepararAssinatura: (id, body) =>
    api.post(`${GEOURB}/projetos/${id}/assinar`, body).then((r) => r.data),
  listarAssinaturas: (id) =>
    api.get(`${GEOURB}/projetos/${id}/assinaturas`).then((r) => r.data),
  // Assinatura desenhada do PROPRIETÁRIO (Requerimento + ART/TRT) via WhatsApp
  propPreparar: (id) => api.post(`${GEOURB}/projetos/${id}/proprietario/preparar`).then((r) => r.data),
  propPosicionar: (id, body) => api.post(`${GEOURB}/projetos/${id}/proprietario/posicionar`, body).then((r) => r.data),
  propSessao: (id) => api.get(`${GEOURB}/projetos/${id}/proprietario/sessao`).then((r) => r.data),
  propReenviar: (id) => api.post(`${GEOURB}/projetos/${id}/proprietario/reenviar`).then((r) => r.data),
  propReset: (id) => api.post(`${GEOURB}/projetos/${id}/proprietario/reset`).then((r) => r.data),
  // Envio de PDF por WhatsApp a um contato qualquer
  enviarWhatsapp: (id, body) => api.post(`${GEOURB}/projetos/${id}/enviar-whatsapp`, body).then((r) => r.data),
  // Capa "Lupa Geo"
  capaPreview: (id) =>
    api.get(`${GEOURB}/projetos/${id}/capa/preview`, { responseType: 'blob' }).then((r) => r.data),
  // Usucapião Extrajudicial
  criarSeedUsucapiao: () => api.post(`${GEOURB}/projetos/seed-usucapiao`).then((r) => r.data),
  usucapiaoValidacao: (id, anoRef) =>
    api.get(`${GEOURB}/projetos/${id}/usucapiao/validacao`,
      { params: { ...(anoRef ? { ano_ref: anoRef } : {}) } }).then((r) => r.data),
  usucapiaoChecklist: (id) =>
    api.get(`${GEOURB}/projetos/${id}/usucapiao/checklist`).then((r) => r.data),
  usucapiaoSeedJuridico: (id) =>
    api.post(`${GEOURB}/projetos/${id}/usucapiao/seed-juridico`).then((r) => r.data),
  usucapiaoAnuenciaPdf: (id, aid, modo, tema) =>
    api.get(`${GEOURB}/projetos/${id}/usucapiao/anuencia/${aid}`,
      { params: { ...(modo ? { modo } : {}), ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  // ── Fase 6 — Georreferenciamento de lote urbano (localização e situação) ──
  georrefOpcoes: () => api.get(`${GEOURB}/georref-urbano/opcoes`).then((r) => r.data),
  georrefComposicao: (id, body) =>
    api.post(`${GEOURB}/projetos/${id}/georref/composicao`, body).then((r) => r.data),
  georrefComposicaoPreview: (id) =>
    api.get(`${GEOURB}/projetos/${id}/georref/composicao/preview`).then((r) => r.data),
  georrefImportCoordenadas: (id, file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post(`${GEOURB}/projetos/${id}/georref/coordenadas/import`, fd).then((r) => r.data);
  },
  georrefQuadra: (id, body) => api.post(`${GEOURB}/projetos/${id}/georref/quadra`, body).then((r) => r.data),
  georrefValidar: (id) => api.post(`${GEOURB}/projetos/${id}/georref/validar`).then((r) => r.data),
  georrefExtrair: (id) => api.post(`${GEOURB}/projetos/${id}/georref/extrair`).then((r) => r.data),
  georrefDocumento: (id, tipo, tema) =>
    api.get(`${GEOURB}/projetos/${id}/georref/documento/${tipo}`,
      { params: { ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  georrefDossie: (id, tema) =>
    api.get(`${GEOURB}/projetos/${id}/georref/dossie`,
      { params: { ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  georrefCapaPreview: (id, tema) =>
    api.get(`${GEOURB}/projetos/${id}/georref/capa/preview`,
      { params: { ...(tema ? { tema } : {}) }, responseType: 'blob' }).then((r) => r.data),
  // Presets de composição (cross-módulo: georref/geo_urbano/onr)
  listarPresets: (modulo) =>
    api.get(`${GEOURB}/presets`, { params: modulo ? { modulo } : {} }).then((r) => r.data),
  criarPreset: (body) => api.post(`${GEOURB}/presets`, body).then((r) => r.data),
  excluirPreset: (prid) => api.delete(`${GEOURB}/presets/${prid}`).then((r) => r.data),
  // Link público do dossiê (paridade com o card do PTAM)
  gerarLink: (id) => api.post(`${GEOURB}/projetos/${id}/link`).then((r) => r.data),
  desativarLink: (id) => api.delete(`${GEOURB}/projetos/${id}/link`).then((r) => r.data),
};

// Arquivo ONR (SIG-RI) STANDALONE — sobe mapa+memorial+ART+certidão → extrai → gera shapefile
const ONRSIG = '/topografia/onr-sigri';
export const onrSigriAPI = {
  listar: () => api.get(`${ONRSIG}/jobs`).then((r) => r.data),
  criar: (data) => api.post(`${ONRSIG}/jobs`, data).then((r) => r.data),
  obter: (id) => api.get(`${ONRSIG}/jobs/${id}`).then((r) => r.data),
  atualizar: (id, data) => api.patch(`${ONRSIG}/jobs/${id}`, data).then((r) => r.data),
  excluir: (id) => api.delete(`${ONRSIG}/jobs/${id}`).then((r) => r.data),
  upload: (id, tipo, file) => {
    const fd = new FormData();
    fd.append('tipo', tipo);
    fd.append('file', file);
    return api.post(`${ONRSIG}/jobs/${id}/upload`, fd).then((r) => r.data);
  },
  removerUpload: (id, tipo, itemId) =>
    api.delete(`${ONRSIG}/jobs/${id}/uploads/${tipo}/${itemId}`).then((r) => r.data),
  extrair: (id) => api.post(`${ONRSIG}/jobs/${id}/extrair`).then((r) => r.data),
  validar: (id) => api.post(`${ONRSIG}/jobs/${id}/validar`).then((r) => r.data),
  justificar: (id, codigo, texto) =>
    api.post(`${ONRSIG}/jobs/${id}/justificar`, { codigo, texto }).then((r) => r.data),
  geojson: (id) => api.get(`${ONRSIG}/jobs/${id}/geojson`).then((r) => r.data),
  preview: (id) => api.post(`${ONRSIG}/jobs/${id}/preview`).then((r) => r.data),
  shapefile: (id) => api.get(`${ONRSIG}/jobs/${id}/shapefile`, { responseType: 'blob' }).then((r) => r.data),
  kml: (id) => api.get(`${ONRSIG}/jobs/${id}/kml`, { responseType: 'blob' }).then((r) => r.data),
  // Anexos do processo (classificar/renomear/reordenar/visualizar)
  tiposAnexo: () => api.get(`${ONRSIG}/tipos-anexo`).then((r) => r.data),
  anexoUpload: (id, file, tipo, nome) => {
    const fd = new FormData();
    fd.append('file', file);
    if (tipo) fd.append('tipo', tipo);
    if (nome) fd.append('nome', nome);
    return api.post(`${ONRSIG}/jobs/${id}/anexo`, fd).then((r) => r.data);
  },
  anexoAtualizar: (id, aid, data) => api.patch(`${ONRSIG}/jobs/${id}/anexo/${aid}`, data).then((r) => r.data),
  anexoOrdem: (id, ordem) => api.post(`${ONRSIG}/jobs/${id}/anexos/ordem`, { ordem }).then((r) => r.data),
  anexoExcluir: (id, aid) => api.delete(`${ONRSIG}/jobs/${id}/anexo/${aid}`).then((r) => r.data),
  anexoView: (id, aid) => api.get(`${ONRSIG}/jobs/${id}/anexo/${aid}`, { responseType: 'blob' }).then((r) => r.data),
};

// Geo Urbano — assinatura pública do proprietário (página mobile, sem auth)
export const geoUrbanoPublicoAPI = {
  obter: (token) => api.get(`/publico/geo-urbano/${token}`).then((r) => r.data),
  assinar: (token, body) => api.post(`/publico/geo-urbano/${token}`, body).then((r) => r.data),
};

// Testemunhas — gestão (autenticada) + público (link tokenizado)
export const testemunhasAssinaturaAPI = {
  cadastrar: (modulo, docId, testemunhas) =>
    api.post(`/testemunhas-assinatura/${modulo}/${docId}`, { testemunhas }).then((r) => r.data),
  preparar: (modulo, docId) =>
    api.get(`/testemunhas-assinatura/${modulo}/${docId}/preparar`).then((r) => r.data),
  posicionar: (modulo, docId, posicoes) =>
    api.post(`/testemunhas-assinatura/${modulo}/${docId}/posicionar`, { posicoes }).then((r) => r.data),
  enviarTodas: (modulo, docId, body) =>
    api.post(`/testemunhas-assinatura/${modulo}/${docId}/enviar`, body || {}).then((r) => r.data),
  reenviar: (modulo, docId, tid) =>
    api.post(`/testemunhas-assinatura/${modulo}/${docId}/${tid}/reenviar`).then((r) => r.data),
  editar: (modulo, docId, tid, body) =>
    api.put(`/testemunhas-assinatura/${modulo}/${docId}/${tid}`, body).then((r) => r.data),
  excluir: (modulo, docId, tid) =>
    api.delete(`/testemunhas-assinatura/${modulo}/${docId}/${tid}`).then((r) => r.data),
  enviarDocumento: (modulo, docId, tid, body) =>
    api.post(`/testemunhas-assinatura/${modulo}/${docId}/${tid}/documento`, body).then((r) => r.data),
  removerDocumento: (modulo, docId, tid) =>
    api.delete(`/testemunhas-assinatura/${modulo}/${docId}/${tid}/documento`).then((r) => r.data),
  documentoPreview: (modulo, docId, tid) =>
    api.get(`/testemunhas-assinatura/${modulo}/${docId}/${tid}/documento/preview`, { responseType: 'blob' }).then((r) => r.data),
  status: (modulo, docId) =>
    api.get(`/testemunhas-assinatura/${modulo}/${docId}/status`).then((r) => r.data),
};
export const testemunhaPublicoAPI = {
  obter: (token) => api.get(`/publico/testemunha/${token}`).then((r) => r.data),
  enviarDocumento: (token, body) => api.post(`/publico/testemunha/${token}/documento`, body).then((r) => r.data),
  assinar: (token, body) => api.post(`/publico/testemunha/${token}/assinar`, body).then((r) => r.data),
};
