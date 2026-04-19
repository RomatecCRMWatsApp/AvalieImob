import React from 'react';
import Navbar from '../components/landing/Navbar';
import Hero from '../components/landing/Hero';
import Features from '../components/landing/Features';
import Services from '../components/landing/Services';
import Flow from '../components/landing/Flow';
import Pricing from '../components/landing/Pricing';
import About from '../components/landing/About';
import CeoSection from '../components/landing/CeoSection';
import Footer from '../components/landing/Footer';
import WhatsAppButton from '../components/landing/WhatsAppButton';

const LandingPage = () => {
  return (
    <div className="bg-white">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <Services />
        <Flow />
        <Pricing />
        <About />
        <CeoSection />
      </main>
      <Footer />
      <WhatsAppButton />
    </div>
  );
};

export default LandingPage;
