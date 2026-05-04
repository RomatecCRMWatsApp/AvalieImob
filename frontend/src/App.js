import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/toaster';
import InstallPrompt from './components/common/InstallPrompt';
import RomaIAWidget from './components/common/RomaIAWidget';

import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import PortalCliente from './pages/PortalCliente';
import ContratoPublico from './pages/ContratoPublico';
import ServicoPTAM from './pages/ServicoPTAM';
import ServicoLaudoTecnico from './pages/ServicoLaudoTecnico';
import ServicoAvaliacaoRural from './pages/ServicoAvaliacaoRural';
import ServicoAvaliacaoGarantia from './pages/ServicoAvaliacaoGarantia';
import ServicoAvaliacaoUrbana from './pages/ServicoAvaliacaoUrbana';
import Blog from './pages/Blog';
import BlogPostComoFazerPTAM from './pages/blog/BlogPostComoFazerPTAM';
import BlogPostPtamLaudo from './pages/blog/BlogPostPtamLaudo';
import BlogPostAvaliacaoRural from './pages/blog/BlogPostAvaliacaoRural';
import BlogPostVLF from './pages/blog/BlogPostVLF';

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
  if (loading) return <div className="min-h-screen flex items-center justify-center">Carregando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center">Carregando...</div>;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
};

function App() {
  return (
    <div className="App">
      <HelmetProvider>
        <AuthProvider>
          <BrowserRouter>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/servicos/ptam" element={<ServicoPTAM />} />
                <Route path="/servicos/laudo-tecnico" element={<ServicoLaudoTecnico />} />
                <Route path="/servicos/avaliacao-rural" element={<ServicoAvaliacaoRural />} />
                <Route path="/servicos/avaliacao-garantia" element={<ServicoAvaliacaoGarantia />} />
                <Route path="/servicos/avaliacao-urbana" element={<ServicoAvaliacaoUrbana />} />
                <Route path="/blog" element={<Blog />} />
                <Route path="/blog/como-fazer-ptam-passo-a-passo-nbr-14653" element={<BlogPostComoFazerPTAM />} />
                <Route path="/blog/diferenca-ptam-laudo-avaliacao-imobiliaria" element={<BlogPostPtamLaudo />} />
                <Route path="/blog/avaliacao-imovel-rural-nbr-14653-3-guia-completo" element={<BlogPostAvaliacaoRural />} />
                <Route path="/blog/como-calcular-valor-liquidacao-forcada-vlf" element={<BlogPostVLF />} />
                <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
                <Route path="/cadastro" element={<PublicRoute><Register /></PublicRoute>} />
                <Route path="/laudo/:token" element={<PortalCliente />} />
                <Route path="/contrato/public/:token" element={<ContratoPublico />} />
                <Route path="/dashboard/*" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
            <Toaster />
            <InstallPrompt />
            <RomaIAWidget />
          </BrowserRouter>
        </AuthProvider>
      </HelmetProvider>
    </div>
  );
}

export default App;
