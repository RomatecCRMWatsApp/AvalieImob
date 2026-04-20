import React, { useRef, useState, useEffect } from 'react';
import { Home, Bed, Bath, Maximize2, MapPin, ExternalLink, Building2 } from 'lucide-react';
import { imoveisAPI } from '../../lib/api';

const formatPreco = (valor) => {
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  if (!num || isNaN(num)) return 'Consulte';
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0 });
};

const PLACEHOLDER_GRADIENTS = [
  'from-emerald-800 to-emerald-950',
  'from-teal-800 to-teal-950',
  'from-green-800 to-green-950',
  'from-cyan-800 to-cyan-950',
  'from-emerald-700 to-teal-900',
];

/**
 * Normaliza um imóvel vindo do tRPC para o formato do carrossel.
 * O CRM pode retornar campos em snake_case ou camelCase.
 */
function normalizeImovel(raw) {
  const fotos = raw.photos || raw.fotos || raw.images || [];
  const primeiraFoto = Array.isArray(fotos) && fotos.length > 0
    ? (typeof fotos[0] === 'string' ? fotos[0] : fotos[0]?.url || fotos[0]?.src || null)
    : null;

  return {
    nome: raw.name || raw.nome || raw.title || raw.titulo || 'Imóvel',
    tipo: raw.type || raw.tipo || raw.category || 'Imóvel',
    preco: raw.price || raw.preco || raw.valor || raw.salePrice || 0,
    endereco: raw.address || raw.endereco || raw.location || '',
    quartos: raw.bedrooms ?? raw.quartos ?? raw.rooms ?? null,
    banheiros: raw.bathrooms ?? raw.banheiros ?? null,
    vagas: raw.parkingSpots ?? raw.vagas ?? raw.parking ?? null,
    area: raw.area ?? raw.buildingArea ?? raw.builtArea ?? null,
    terreno: raw.landArea ?? raw.terreno ?? null,
    imagem: primeiraFoto,
    fotos: Array.isArray(fotos) ? fotos.length : 0,
    link: raw.url || raw.link || 'https://romateccrm.com/properties',
    status: raw.status || 'Disponível',
  };
}

const ImovelCard = ({ imovel, index }) => {
  const isChacara = imovel.tipo === 'Chácara' || imovel.tipo === 'Chacara';
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
  const [imoveis, setImoveis] = useState([]);
  const [loading, setLoading] = useState(true);

  // Busca imóveis da API do CRM
  // O backend retorna { imoveis: [...], cached: bool } com campos já normalizados
  useEffect(() => {
    let cancelled = false;
    imoveisAPI.list()
      .then((data) => {
        if (cancelled) return;
        // Suporte a { imoveis: [...] } (backend atual) e array direto (fallback)
        const raw = Array.isArray(data) ? data : (data?.imoveis ?? []);
        const lista = raw.map(normalizeImovel);
        setImoveis(lista);
      })
      .catch(() => {
        // fallback silencioso: mantém lista vazia
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  // Duplicar lista para loop infinito suave
  const items = imoveis.length > 0 ? [...imoveis, ...imoveis] : [];

  useEffect(() => {
    const track = trackRef.current;
    if (!track || items.length === 0) return;

    positionRef.current = 0;
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
  }, [paused, items.length]);

  // Oculta a seção se carregou mas não há imóveis
  if (!loading && imoveis.length === 0) return null;

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
      {loading ? (
        <div className="text-center py-12">
          <span className="text-gray-400 text-sm animate-pulse">Carregando imóveis...</span>
        </div>
      ) : (
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
                <ImovelCard key={`${imovel.nome}-${i}`} imovel={imovel} index={i % imoveis.length} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Indicador de pausa */}
      {paused && !loading && (
        <div className="text-center mt-6">
          <span className="text-gray-500 text-xs italic">Carrossel pausado — mova o mouse para fora para continuar</span>
        </div>
      )}
    </section>
  );
};

export default ImoveisCarousel;
