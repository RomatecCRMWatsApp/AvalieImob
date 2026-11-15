// @page Planos — página pública só com os valores da assinatura (/planos).
// Link curto para responder "qual o valor?" no WhatsApp sem mandar a landing inteira.
import React from 'react';
import SEO from '../components/common/SEO';
import Navbar from '../components/landing/Navbar';
import Pricing from '../components/landing/Pricing';
import Footer from '../components/landing/Footer';
import WhatsAppButton from '../components/landing/WhatsAppButton';

export default function Planos() {
  return (
    <>
      <SEO
        title="Planos e valores da assinatura"
        description="Mensal R$ 89,90, trimestral R$ 239,90 ou anual R$ 849,90. Cadastre-se e teste o AvalieImob grátis por 3 dias."
        url="https://www.romatecavalieimob.com.br/planos"
      />
      <div className="bg-white pt-28">
        <Navbar />
        <main>
          <Pricing />
          <div className="text-center pb-16 -mt-10 px-6 text-sm text-gray-600">
            Ao criar a conta você ganha <strong>3 dias de teste grátis</strong>. Dúvidas? Fale no WhatsApp{' '}
            <a className="text-emerald-800 underline" href="https://wa.me/5599991811246" target="_blank" rel="noopener noreferrer">(99) 99181-1246</a>.
          </div>
        </main>
        <Footer />
        <WhatsAppButton />
      </div>
    </>
  );
}
