import React from 'react';
import Navbar from '../components/landing/Navbar';
import Hero from '../components/landing/Hero';
import Features from '../components/landing/Features';
import Services from '../components/landing/Services';
import Flow from '../components/landing/Flow';
import Pricing from '../components/landing/Pricing';
import About from '../components/landing/About';
import Footer from '../components/landing/Footer';

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
      </main>
      <Footer />
    </div>
  );
};

export default LandingPage;
