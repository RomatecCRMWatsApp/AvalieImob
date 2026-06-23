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

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught:', error, info);
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', padding: '2rem' }}>
          <h2 style={{ color: '#b91c1c', marginBottom: '1rem' }}>Algo deu errado</h2>
          <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>Recarregue a página ou tente novamente.</p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/'; }}
            style={{ background: '#064e3b', color: '#fff', border: 'none', borderRadius: '6px', padding: '0.6rem 1.5rem', cursor: 'pointer', fontSize: '1rem' }}
          >
            Voltar ao início
          </button>
        </div>
      );
    }
    return this.props.children;
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
