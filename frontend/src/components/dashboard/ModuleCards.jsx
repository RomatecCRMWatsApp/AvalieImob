// @module dashboard/ModuleCards — acesso rápido aos módulos principais.
// Rotas reais do painel; artes da campanha (recorte sem texto) (ilustrações decorativas, alt
// vazio porque o título do cartão já identifica o módulo).
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const MODULOS = [
  {
    to: '/dashboard/ptam',
    titulo: 'PTAM e laudos',
    texto: 'Elabore e acompanhe seus pareceres de avaliação.',
    img: 'modulo-ptam',
  },
  {
    to: '/dashboard/topografia/georef',
    titulo: 'Georreferenciamento',
    texto: 'Memorial, vértices, peças do protocolo e dossiê.',
    img: 'modulo-georreferenciamento',
  },
  {
    to: '/dashboard/contratos',
    titulo: 'Contratos',
    texto: 'Contratos, exclusividade e assinatura do cliente.',
    img: 'modulo-contratos',
  },
  {
    to: '/dashboard/topografia/onr-sigri',
    titulo: 'Shapefile urbano (ONR)',
    texto: 'Pacote do lote urbano para envio ao SIG-RI.',
    img: 'modulo-onr',
  },
];

const ModuleCards = () => (
  <section aria-labelledby="av-acesso-rapido">
    <h2 id="av-acesso-rapido" style={{ fontSize: 18, fontWeight: 700, color: 'var(--av-text)', marginBottom: 12 }}>
      Acesso rápido
    </h2>
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4">
      {MODULOS.map((m) => (
        <Link key={m.to} to={m.to} className="av-card av-module-card" style={{ background: '#0C3320', borderColor: 'rgba(201,168,76,.35)' }}>
          <img
            src={`/modulos/${m.img}-640.webp`}
            srcSet={`/modulos/${m.img}-640.webp 640w, /modulos/${m.img}.webp 1600w`}
            sizes="(min-width: 1280px) 22vw, 46vw"
            width="640"
            height="360"
            alt=""
            loading="lazy"
            decoding="async"
          />
          <span className="flex flex-col gap-1 p-3 sm:p-4 flex-1" style={{ borderTop: '1px solid rgba(201,168,76,.35)' }}>
            <span className="text-sm sm:text-base" style={{ fontWeight: 700, color: '#F3F1E6', overflowWrap: 'anywhere' }}>{m.titulo}</span>
            <span className="hidden sm:block" style={{ fontSize: 13, color: '#C9D8CE' }}>{m.texto}</span>
            <span className="inline-flex items-center gap-1 mt-auto pt-2" style={{ fontSize: 13, fontWeight: 600, color: '#E0C264' }}>
              Abrir módulo <ArrowRight size={14} aria-hidden="true" />
            </span>
          </span>
        </Link>
      ))}
    </div>
  </section>
);

export default ModuleCards;
