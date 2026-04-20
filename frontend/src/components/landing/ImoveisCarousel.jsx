import React, { useRef, useState, useEffect } from 'react';
import { Home, Bed, Bath, Maximize2, MapPin, ExternalLink, Building2 } from 'lucide-react';

const IMOVEIS_CRM = [
  {
    nome: 'ALACIDE',
    tipo: 'Casa',
    preco: 380000,
    endereco: 'AV-Tocantins, Quadra 38 Lote 01, Açailândia',
    quartos: 3,
    banheiros: 2,
    vagas: 1,
    area: 127.52,
    terreno: 300,
    fotos: 16,
    imagem: null,
    link: 'https://romateccrm.com/properties',
    status: 'Disponível',
  },
  {
    nome: 'Mod_Vaz-01',
    tipo: 'Casa',
    preco: 300000,
    endereco: 'Rua João Mariquinha, Quadra 15 Lote 12, Açailândia',
    quartos: 3,
    banheiros: 2,
    vagas: 1,
    area: 75.79,
    terreno: 140.55,
    fotos: 9,
    imagem: null,
    link: 'https://romateccrm.com/properties',
    status: 'Disponível',
  },
  {
    nome: 'Mod_Vaz-03',
    tipo: 'Casa',
    preco: 210000,
    endereco: 'Rua Salomão Awad, Quadra 11 Lote 10E, Açailândia',
    quartos: 2,
    banheiros: 2,
    vagas: 1,
    area: 63.85,
    terreno: 150,
    fotos: 7,
    imagem: null,
    link: 'https://romateccrm.com/properties',
    status: 'Disponível',
  },
  {
    nome: 'Condomínio de Chácaras Giuliano',
    tipo: 'Chácara',
    preco: 160000,
    endereco: 'Açailândia',
    quartos: null,
    banheiros: null,
    vagas: null,
    area: 1000,
    terreno: 1000,
    fotos: 0,
    imagem: null,
    link: 'https://romateccrm.com/properties',
    status: 'Disponível',
  },
  {
    nome: 'Mod_Vaz-02',
    tipo: 'Casa',
    preco: 250000,
    endereco: 'Rua Amaro Pedroza, Açailândia',
    quartos: 3,
    banheiros: 2,
    vagas: null,
    area: 65.42,
    terreno: null,
    fotos: 0,
    imagem: null,
    link: 'https://romateccrm.com/properties',
    status: 'Disponível',
  },
];

const formatPreco = (valor) =>
  valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0 });

const PLACEHOLDER_GRADIENTS = [
  'from-emerald-800 to-emerald-950',
  'from-teal-800 to-teal-950',
  'from-green-800 to-green-950',
  'from-cyan-800 to-cyan-950',
  'from-emerald-700 to-teal-900',
];

const ImovelCard = ({ imovel, index }) => {
  const isChacara = imovel.tipo === 'Chácara';
  const gradient = PLACEHOLDER_GRADIENTS[index % PLACEHOLDER_GRADIENTS.length];

  return (
    <div className="flex-none w-72 sm:w-80 bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:border-amber-400/40 transition-all duration-300 group">
      {/* Imagem / Placeholder */}
      <div className={`relative h-44 bg-gradient-to-br ${gradient} flex items-center justify-center overflow-hidden`}>
        {imovel.imagem ? (
          <img
            src={imovel.imagem}
            alt={imovel.nome}
            className="w-full h-full object-cover"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 opacity-40">
            {isChacara ? (
              <Building2 className="w-16 h-16 text-white" />
            ) : (
              <Home className="w-16 h-16 text-white" />
            )}
            <span className="text-white text-xs font-medium uppercase tracking-widest">Sem foto</span>
          </div>
        )}

        {/* Badges sobrepostos */}
        <div className="absolute top-3 left-3 flex gap-2">
          <span className={`px-2.5 py-1 rounded-full text-xs font-bold tracking-wide ${isChacara ? 'bg-amber-500 text-black' : 'bg-emerald-500 text-white'}`}>
            {imovel.tipo}
          </span>
        </div>
        <div className="absolute top-3 right-3">
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-green-500/90 text-white">
            {imovel.status}
          </span>
        </div>

        {/* Fotos count */}
        {imovel.fotos > 0 && (
          <div className="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-2 py-0.5 rounded-full">
            {imovel.fotos} fotos
          </div>
        )}
      </div>

      {/* Conteúdo */}
      <div className="p-5 flex flex-col gap-3">
        <div>
          <p className="text-amber-400 text-xl font-bold">{formatPreco(imovel.preco)}</p>
          <h3 className="text-white font-bold text-base mt-0.5 truncate">{imovel.nome}</h3>
          <div className="flex items-start gap-1.5 mt-1">
            <MapPin className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
            <p className="text-gray-400 text-xs leading-snug line-clamp-2">{imovel.endereco}</p>
          </div>
        </div>

        {/* Atributos */}
        <div className="flex items-center gap-3 text-gray-300 text-xs border-t border-white/10 pt-3 flex-wrap">
          {imovel.quartos != null && (
            <span className="flex items-center gap-1">
              <Bed className="w-3.5 h-3.5" /> {imovel.quartos} quartos
            </span>
          )}
          {imovel.banheiros != null && (
            <span className="flex items-center gap-1">
              <Bath className="w-3.5 h-3.5" /> {imovel.banheiros} banh.
            </span>
          )}
          {imovel.area != null && (
            <span className="flex items-center gap-1">
              <Maximize2 className="w-3.5 h-3.5" /> {imovel.area} m²
            </span>
          )}
        </div>

        {/* Botão */}
        <a
          href={imovel.link}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold transition-colors mt-1"
        >
          Ver no Portal <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
};

const ImoveisCarousel = () => {
  const trackRef = useRef(null);
  const [paused, setPaused] = useState(false);
  const animationRef = useRef(null);
  const positionRef = useRef(0);

  // Duplicar lista para loop infinito suave
  const items = [...IMOVEIS_CRM, ...IMOVEIS_CRM];

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    const SPEED = 0.5; // px por frame
    const totalWidth = track.scrollWidth / 2;

    const step = () => {
      if (!paused) {
        positionRef.current += SPEED;
        if (positionRef.current >= totalWidth) {
          positionRef.current = 0;
        }
        track.style.transform = `translateX(-${positionRef.current}px)`;
      }
      animationRef.current = requestAnimationFrame(step);
    };

    animationRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationRef.current);
  }, [paused]);

  return (
    <section id="imoveis" className="py-20 bg-gray-900 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 mb-10">
        <div className="text-center">
          <div className="text-xs font-semibold tracking-[0.2em] text-amber-400 mb-3 uppercase">
            Portal Romatec CRM
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-white leading-tight mb-4">
            Imóveis <span className="text-amber-400">Disponíveis</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-xl mx-auto">
            Confira nosso portfólio de imóveis à venda. Qualidade e confiança Romatec.
          </p>
          <a
            href="https://romateccrm.com/properties"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 mt-6 px-6 py-3 rounded-full border border-amber-400/40 text-amber-400 text-sm font-semibold hover:bg-amber-400/10 transition-colors"
          >
            Ver todos os imóveis no Portal <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Carrossel */}
      <div
        className="relative w-full"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {/* Gradientes laterais */}
        <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-24 z-10 bg-gradient-to-r from-gray-900 to-transparent" />
        <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-24 z-10 bg-gradient-to-l from-gray-900 to-transparent" />

        <div className="overflow-hidden px-6">
          <div
            ref={trackRef}
            className="flex gap-5 will-change-transform"
            style={{ width: 'max-content' }}
          >
            {items.map((imovel, i) => (
              <ImovelCard key={`${imovel.nome}-${i}`} imovel={imovel} index={i % IMOVEIS_CRM.length} />
            ))}
          </div>
        </div>
      </div>

      {/* Indicador de pausa */}
      {paused && (
        <div className="text-center mt-6">
          <span className="text-gray-500 text-xs italic">Carrossel pausado — mova o mouse para fora para continuar</span>
        </div>
      )}
    </section>
  );
};

export default ImoveisCarousel;
