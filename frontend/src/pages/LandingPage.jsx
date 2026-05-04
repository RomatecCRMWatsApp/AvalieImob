import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import SEO from '../components/common/SEO';
import Navbar from '../components/landing/Navbar';
import Hero from '../components/landing/Hero';
import Features from '../components/landing/Features';
import Services from '../components/landing/Services';
import Flow from '../components/landing/Flow';
import Pricing from '../components/landing/Pricing';
import About from '../components/landing/About';
import CeoSection from '../components/landing/CeoSection';
import ImoveisCarousel from '../components/landing/ImoveisCarousel';
import Footer from '../components/landing/Footer';
import WhatsAppButton from '../components/landing/WhatsAppButton';

const WelcomeBanner = () => {
  const token = localStorage.getItem('romatec_token');
  const userStr = localStorage.getItem('romatec_user');
  if (!token || !userStr) return null;

  let user;
  try { user = JSON.parse(userStr); } catch { return null; }
  const firstName = user?.name?.split(' ')[0] || 'Usuário';

  return (
    <div className="bg-gradient-to-r from-emerald-900 to-emerald-800 text-white">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Bem-vindo, {firstName}! 👋</h2>
          <p className="text-emerald-200 text-sm">Confira nossos serviços abaixo ou acesse seu painel de controle.</p>
        </div>
        <Link to="/dashboard" className="flex items-center gap-2 bg-white text-emerald-900 px-5 py-2.5 rounded-lg font-semibold text-sm hover:bg-emerald-50 transition-colors">
          Meu Dashboard <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
};

const LandingPage = () => {
  return (
    <>
      <SEO
        url="https://www.romatecavalieimob.com.br/"
        keywords="software PTAM online, sistema avaliacao imobiliaria, emitir PTAM online, laudo avaliacao imovel, NBR 14.653, avaliacao de garantias, kit TVI, avaliacao imovel rural, semoventes penhor rural"
      />
      <div className="bg-white pt-28">
        <Navbar />
        <WelcomeBanner />
        <main>
          <Hero />
          <Features />
          <Services />
          <Flow />
          <Pricing />
          <About />
          <CeoSection />
          <ImoveisCarousel />
        </main>
        <Footer />
        <WhatsAppButton />
      </div>
    </>
  );
};

export default LandingPage;
