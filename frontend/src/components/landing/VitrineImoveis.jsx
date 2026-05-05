// @component VitrineImoveis — vitrine moderna de tipos de imóveis avaliados.
// Substitui a antiga seção 3D (removida em commit anterior).
//
// Layout: grid 3x2 desktop / 2x3 tablet / 1 coluna mobile.
// Imagens reais do Unsplash em /public/img/tipos-imoveis/ (lazy-loaded).
// Parallax sutil: cada card recebe translateY(±) conforme scroll.
// Hover: borda dourada + zoom suave da imagem + ícone Lucide cresce.
//
// Posicao na landing: entre <Services /> e <Flow />.
import React, { useEffect, useRef } from 'react';
import { Building2, Home, Store, Warehouse, Trees, Map } from 'lucide-react';

const TIPOS = [
  {
    img: '/img/tipos-imoveis/residencial.jpg',
    titulo: 'Residencial Urbano',
    descricao: 'Casas, sobrados e residências em áreas urbanas',
    icon: Home,
  },
  {
    img: '/img/tipos-imoveis/apartamento.jpg',
    titulo: 'Apartamentos',
    descricao: 'Unidades em condomínios e edifícios residenciais',
    icon: Building2,
  },
  {
    img: '/img/tipos-imoveis/comercial.jpg',
    titulo: 'Imóveis Comerciais',
    descricao: 'Lojas, salas comerciais e pontos de negócio',
    icon: Store,
  },
  {
    img: '/img/tipos-imoveis/galpao.jpg',
    titulo: 'Galpões e Industriais',
    descricao: 'Galpões logísticos, industriais e armazéns',
    icon: Warehouse,
  },
  {
    img: '/img/tipos-imoveis/rural.jpg',
    titulo: 'Imóveis Rurais',
    descricao: 'Sítios, fazendas e propriedades rurais produtivas',
    icon: Trees,
  },
  {
    img: '/img/tipos-imoveis/terreno.jpg',
    titulo: 'Terrenos e Lotes',
    descricao: 'Lotes urbanos, glebas e áreas para incorporação',
    icon: Map,
  },
];

export default function VitrineImoveis() {
  const sectionRef = useRef(null);

  // Parallax suave: cada card recebe um translateY proporcional ao scroll,
  // alternando direcoes (cards pares sobem, ímpares descem) pra criar
  // movimento sutil e nao-monotono.
  useEffect(() => {
    const handleScroll = () => {
      if (!sectionRef.current) return;
      const cards = sectionRef.current.querySelectorAll('[data-parallax]');
      const rect = sectionRef.current.getBoundingClientRect();
      const sectionTop = rect.top;
      const sectionHeight = rect.height;
      const windowHeight = window.innerHeight;

      // Progresso 0..1 conforme a section atravessa o viewport
      const progress = 1 - (sectionTop + sectionHeight) / (windowHeight + sectionHeight);

      cards.forEach((card, i) => {
        const offset = (i % 2 === 0 ? -1 : 1) * progress * 30;
        card.style.transform = `translateY(${offset}px)`;
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative py-24 md:py-32 bg-gradient-to-b from-[#0a1f18] via-[#0d4f3c] to-[#0a1f18] overflow-hidden"
    >
      {/* Header */}
      <div className="container mx-auto px-6 mb-16 text-center">
        <span className="inline-block text-[#c9a84c] font-semibold tracking-widest text-sm uppercase mb-4">
          Cobertura Completa
        </span>
        <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 leading-tight">
          Avaliamos qualquer
          <br />
          <span className="text-[#c9a84c]">tipo de imóvel</span>
        </h2>
        <p className="text-lg text-white/70 max-w-2xl mx-auto">
          Sistema especializado em PTAM, laudos técnicos e avaliações de garantia
          conforme NBR 14.653, para todos os perfis de imóveis.
        </p>
      </div>

      {/* Grid de cards com parallax */}
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
          {TIPOS.map((tipo, i) => {
            const Icon = tipo.icon;
            return (
              <div
                key={tipo.titulo}
                data-parallax
                className="group relative overflow-hidden rounded-2xl aspect-[4/5] cursor-pointer transition-transform duration-700 ease-out"
                style={{ willChange: 'transform' }}
              >
                {/* Imagem de fundo (lazy nativa via <img> oculta + bg pra parallax suave) */}
                <div
                  className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110"
                  style={{ backgroundImage: `url(${tipo.img})` }}
                  role="img"
                  aria-label={tipo.titulo}
                />

                {/* Overlay verde escuro (gradient bottom-up) */}
                <div className="absolute inset-0 bg-gradient-to-t from-[#0a1f18]/95 via-[#0d4f3c]/40 to-transparent" />

                {/* Borda dourada no hover */}
                <div className="absolute inset-0 border-2 border-transparent group-hover:border-[#c9a84c] rounded-2xl transition-colors duration-500" />

                {/* Conteúdo */}
                <div className="absolute bottom-0 left-0 right-0 p-6 md:p-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#c9a84c] mb-4 group-hover:scale-110 transition-transform duration-300">
                    <Icon className="w-6 h-6 text-[#0a1f18]" />
                  </div>
                  <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">
                    {tipo.titulo}
                  </h3>
                  <p className="text-white/80 text-sm md:text-base">
                    {tipo.descricao}
                  </p>
                </div>

                {/* Numeração */}
                <div className="absolute top-6 right-6 text-5xl font-bold text-white/20 group-hover:text-[#c9a84c]/60 transition-colors duration-500">
                  {String(i + 1).padStart(2, '0')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Elementos decorativos sutis no fundo (orbs douradas blur) */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-[#c9a84c]/5 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-[#c9a84c]/5 rounded-full blur-3xl translate-x-1/2 translate-y-1/2 pointer-events-none" />
    </section>
  );
}
