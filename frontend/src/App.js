import React, { lazy, Suspense } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppLoader } from './components/brand/AppLoader';
import { Toaster } from './components/ui/toaster';
import InstallPrompt from './components/common/InstallPrompt';
import RomaIAWidget from './components/common/RomaIAWidget';
import DarkModeToggle from './components/DarkModeToggle';
import ConsultaWidget from './components/consulta/ConsultaWidget';

import LandingPage from './pages/LandingPage';
// Code-splitting: cada página vira um chunk próprio, carregado sob demanda (React.lazy).
// O Dashboard (app logado: PTAM/contratos/NFS-e/mapas/gráficos) era o grosso dos ~3 MB do
// bundle único — agora só baixa ao entrar no /dashboard. A landing carrega leve.
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const PortalCliente = lazy(() => import('./pages/PortalCliente'));
const ContratoPublico = lazy(() => import('./pages/ContratoPublico'));
const AceiteContrato = lazy(() => import('./pages/AceiteContrato'));
const AssinarCliente = lazy(() => import('./pages/AssinarCliente'));
const AssinarDocExt = lazy(() => import('./pages/AssinarDocExt'));
const AssinarGeoUrbano = lazy(() => import('./pages/AssinarGeoUrbano'));
const ComoAssinar = lazy(() => import('./pages/ComoAssinar'));
const AssinarTestemunha = lazy(() => import('./pages/AssinarTestemunha'));
const VerificarContrato = lazy(() => import('./pages/VerificarContrato'));
const CalculadoraPortal = lazy(() => import('./pages/avaliacao/CalculadoraPortal'));
const CalculadoraClassica = lazy(() => import('./pages/avaliacao/CalculadoraClassica'));
const CalculadoraPremium = lazy(() => import('./pages/avaliacao/CalculadoraPremium'));
const ServicoPTAM = lazy(() => import('./pages/ServicoPTAM'));
const ServicoLaudoTecnico = lazy(() => import('./pages/ServicoLaudoTecnico'));
const ServicoAvaliacaoRural = lazy(() => import('./pages/ServicoAvaliacaoRural'));
const ServicoAvaliacaoGarantia = lazy(() => import('./pages/ServicoAvaliacaoGarantia'));
const ServicoAvaliacaoUrbana = lazy(() => import('./pages/ServicoAvaliacaoUrbana'));
const Blog = lazy(() => import('./pages/Blog'));
const BlogPostComoFazerPTAM = lazy(() => import('./pages/blog/BlogPostComoFazerPTAM'));
const BlogPostPtamLaudo = lazy(() => import('./pages/blog/BlogPostPtamLaudo'));
const BlogPostAvaliacaoRural = lazy(() => import('./pages/blog/BlogPostAvaliacaoRural'));
const BlogPostVLF = lazy(() => import('./pages/blog/BlogPostVLF'));
const BlogPostGrauFundamentacao = lazy(() => import('./pages/blog/BlogPostGrauFundamentacao'));
const BlogPostMetodoComparativo = lazy(() => import('./pages/blog/BlogPostMetodoComparativo'));
const BlogPostInventarioPartilha = lazy(() => import('./pages/blog/BlogPostInventarioPartilha'));
const BlogPostART_RRT_TRT = lazy(() => import('./pages/blog/BlogPostART_RRT_TRT'));
const BlogPostContratoExclusividade = lazy(() => import('./pages/blog/BlogPostContratoExclusividade'));
const BlogPostAssinaturaICP = lazy(() => import('./pages/blog/BlogPostAssinaturaICP'));
const BlogPostPropostasConsultoria = lazy(() => import('./pages/blog/BlogPostPropostasConsultoria'));
const VerificarLaudo = lazy(() => import('./pages/VerificarLaudo'));

// Detecta falha ao carregar um chunk lazy (bundle velho em cache vs. deploy novo) —
// causa nº 1 de "não abre" no mobile após um deploy.
function isChunkError(error) {
  const s = (((error && (error.message || error.name)) || '') + ((error && error.stack) || ''));
  return /ChunkLoadError|Loading chunk\s*[\w-]*\s*failed|Loading CSS chunk|dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(s);
}

function _recentReload() {
  try { return Date.now() - (+sessionStorage.getItem('avalie_reload_at') || 0) < 10000; } catch (e) { return false; }
}

async function limparCacheERecarregar() {
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    }
    if (window.caches) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  } catch (e) { /* ignore */ }
  window.location.reload();
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null, showDetail: false, chunkReloading: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error, chunkReloading: isChunkError(error) && !_recentReload() };
  }
  componentDidCatch(error, info) {
    this.setState({ info });
    // Bundle velho: recarrega 1x (busca o bundle novo). Guarda contra loop infinito.
    if (isChunkError(error) && !_recentReload()) {
      try { sessionStorage.setItem('avalie_reload_at', String(Date.now())); } catch (e) { /* */ }
      window.location.reload();
      return;
    }
    if (process.env.NODE_ENV === 'development') console.error('ErrorBoundary:', error, info);
  }
  render() {
    if (!this.state.hasError) return this.props.children;
    const box = { position: 'fixed', inset: 0, zIndex: 99999, background: '#fff', overflowY: 'auto', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', padding: '2rem', textAlign: 'center' };
    if (this.state.chunkReloading) {
      return (<div style={box}><h2 style={{ color: '#064e3b' }}>Atualizando para a nova versão…</h2><p style={{ color: '#6b7280' }}>Só um instante.</p></div>);
    }
    const { error, info, showDetail } = this.state;
    const btn = { color: '#fff', border: 'none', borderRadius: '6px', padding: '0.6rem 1.3rem', cursor: 'pointer', fontSize: '0.95rem', margin: '0.3rem' };
    return (
      <div style={box}>
        <h2 style={{ color: '#b91c1c', marginBottom: '0.5rem' }}>Algo deu errado</h2>
        <p style={{ color: '#6b7280', marginBottom: '1.2rem', maxWidth: 440 }}>Se acabou de atualizar o sistema, limpe o cache. Senão, toque em recarregar.</p>
        <div>
          <button onClick={() => window.location.reload()} style={{ ...btn, background: '#064e3b' }}>Recarregar</button>
          <button onClick={limparCacheERecarregar} style={{ ...btn, background: '#B8860B' }}>Limpar cache e recarregar</button>
          <button onClick={() => window.location.assign('/')} style={{ ...btn, background: '#4b5563' }}>Voltar ao início</button>
        </div>
        <div style={{ marginTop: '1rem' }}>
          <button onClick={() => this.setState((s) => ({ showDetail: !s.showDetail }))}
            style={{ background: 'none', border: 'none', color: '#9ca3af', textDecoration: 'underline', cursor: 'pointer', fontSize: '0.8rem' }}>
            {showDetail ? 'Ocultar detalhe técnico' : 'Ver detalhe técnico'}
          </button>
          {showDetail && (
            <button onClick={() => {
              const txt = [String((error && (error.message || error.name)) || 'erro'), String((error && error.stack) || ''), info && info.componentStack ? '--- componentes ---' + info.componentStack : ''].join('\n\n');
              try { (navigator.clipboard && navigator.clipboard.writeText(txt) || Promise.reject()).then(() => this.setState({ copied: true })).catch(() => {}); } catch (e) { /* */ }
            }}
              style={{ marginLeft: '0.8rem', background: 'none', border: '1px solid #cbd5e1', borderRadius: 6, color: '#334155', cursor: 'pointer', fontSize: '0.8rem', padding: '0.25rem 0.7rem' }}>
              {this.state.copied ? '✓ Copiado' : 'Copiar erro'}
            </button>
          )}
        </div>
        {showDetail && (
          <pre style={{ marginTop: '0.8rem', maxWidth: '92vw', maxHeight: '45vh', overflow: 'auto', textAlign: 'left', background: '#0f172a', color: '#e2e8f0', padding: '1rem', borderRadius: '8px', fontSize: '0.72rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {String((error && (error.message || error.name)) || 'erro')}
            {'\n\n'}{String((error && error.stack) || '')}
            {info && info.componentStack ? '\n\n--- componentes ---' + info.componentStack : ''}
          </pre>
        )}
      </div>
    );
  }
}

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <AppLoader label="Iniciando AvalieImob…" />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <AppLoader label="Iniciando AvalieImob…" />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
};

// v1.0 SEO/leads: captura UTM tags + page_origin assim que o app monta.
// Persiste em sessionStorage pra sobreviver a navegacao SPA (usuario pode
// entrar via /blog/X com utm_source=google, scrollar e so depois clicar em
// "Cadastrar" na rota /cadastro — sem isso a UTM se perde).
function captureUtm() {
  if (typeof window === 'undefined') return;
  try {
    const params = new URLSearchParams(window.location.search);
    const utmKeys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
    const captured = {};
    for (const k of utmKeys) {
      const v = params.get(k);
      if (v) captured[k] = v;
    }
    if (Object.keys(captured).length === 0) return; // nada novo, mantem o que tinha
    captured.page_origin = window.location.pathname + window.location.search;
    captured.captured_at = new Date().toISOString();
    sessionStorage.setItem('utm_data', JSON.stringify(captured));
  } catch (_e) { /* sessionStorage indisponivel (private mode antigo) — ignora */ }
}
captureUtm();

function App() {
  return (
    <div className="App">
      <HelmetProvider>
        <AuthProvider>
          <BrowserRouter>
            <ErrorBoundary>
              <Suspense fallback={<AppLoader label="Carregando…" />}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/servicos/ptam" element={<ServicoPTAM />} />
                <Route path="/servicos/laudo-tecnico" element={<ServicoLaudoTecnico />} />
                <Route path="/servicos/avaliacao-rural" element={<ServicoAvaliacaoRural />} />
                <Route path="/servicos/avaliacao-garantia" element={<ServicoAvaliacaoGarantia />} />
                <Route path="/servicos/avaliacao-urbana" element={<ServicoAvaliacaoUrbana />} />
                {/* SEO v1.1 — aliases curtos pra capturar buscas diretas tipo "ptam" */}
                <Route path="/ptam" element={<ServicoPTAM />} />
                <Route path="/laudo-tecnico" element={<ServicoLaudoTecnico />} />
                <Route path="/avaliacao-rural" element={<ServicoAvaliacaoRural />} />
                <Route path="/avaliacao-garantia" element={<ServicoAvaliacaoGarantia />} />
                <Route path="/avaliacao-urbana" element={<ServicoAvaliacaoUrbana />} />
                <Route path="/avaliacao-imovel" element={<ServicoAvaliacaoUrbana />} />
                <Route path="/avaliacao-imobiliaria" element={<ServicoAvaliacaoUrbana />} />
                <Route path="/blog" element={<Blog />} />
                <Route path="/blog/como-fazer-ptam-passo-a-passo-nbr-14653" element={<BlogPostComoFazerPTAM />} />
                <Route path="/blog/diferenca-ptam-laudo-avaliacao-imobiliaria" element={<BlogPostPtamLaudo />} />
                <Route path="/blog/avaliacao-imovel-rural-nbr-14653-3-guia-completo" element={<BlogPostAvaliacaoRural />} />
                <Route path="/blog/como-calcular-valor-liquidacao-forcada-vlf" element={<BlogPostVLF />} />
                <Route path="/blog/grau-fundamentacao-precisao-nbr-14653" element={<BlogPostGrauFundamentacao />} />
                <Route path="/blog/metodo-comparativo-direto-passo-a-passo" element={<BlogPostMetodoComparativo />} />
                <Route path="/blog/avaliacao-imovel-inventario-partilha" element={<BlogPostInventarioPartilha />} />
                <Route path="/blog/como-emitir-art-rrt-trt-avaliacao-imobiliaria" element={<BlogPostART_RRT_TRT />} />
                <Route path="/blog/contrato-exclusividade-procuracao-corretor-imoveis" element={<BlogPostContratoExclusividade />} />
                <Route path="/blog/assinatura-icp-brasil-laudos-contratos-validade-juridica" element={<BlogPostAssinaturaICP />} />
                <Route path="/blog/precificar-georreferenciamento-demarcacao-averbacao-proposta" element={<BlogPostPropostasConsultoria />} />
                <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
                <Route path="/cadastro" element={<PublicRoute><Register /></PublicRoute>} />
                <Route path="/laudo/:token" element={<PortalCliente />} />
                <Route path="/v/laudo/v/:hash" element={<VerificarLaudo />} />
                <Route path="/contrato/public/:token" element={<ContratoPublico />} />
                <Route path="/aceite/:token" element={<AceiteContrato />} />
                <Route path="/assinar-cliente/:token" element={<AssinarCliente />} />
                <Route path="/assinar-doc/:token" element={<AssinarDocExt />} />
                <Route path="/assinar-geo/:token" element={<AssinarGeoUrbano />} />
                <Route path="/assinar/testemunha/:token" element={<AssinarTestemunha />} />
                <Route path="/como-assinar" element={<ComoAssinar />} />
                <Route path="/verificar/:hash" element={<VerificarContrato />} />
                <Route path="/quanto-vale-meu-imovel" element={<CalculadoraPortal />} />
                <Route path="/avaliacao/classica" element={<CalculadoraClassica />} />
                <Route path="/avaliacao/premium" element={<CalculadoraPremium />} />
                <Route path="/dashboard/*" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
              </Suspense>
            </ErrorBoundary>
            <Toaster />
            <InstallPrompt />
            <RomaIAWidget />
            <ConsultaWidget />
            <DarkModeToggle />
          </BrowserRouter>
        </AuthProvider>
      </HelmetProvider>
    </div>
  );
}

export default App;
