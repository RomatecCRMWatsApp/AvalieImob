// @component Avaliacao3DFallback — versao estatica da secao 3D para mobile
// (<768px) e usuarios com prefers-reduced-motion.
//
// v2 (cena 2 nova): mostra os 3 passos da narrativa COM um grid 3x3 dos
// 9 tipos de imovel avaliados. Cobre o que o canvas R3F mostra na sub-fase
// B (grid organizado). Usa icones Lucide equivalentes a cada componente
// 3D — sem dependencia de Three.js, ~zero impacto no bundle mobile.
import React from 'react';
import {
  Building2, BarChart3, FileText, Home, Building, Warehouse,
  Store, Trees, Map, TreePine, Cog,
} from 'lucide-react';

// 3 passos da narrativa principal (preserva a estrutura da cena 1 -> 2 -> 3)
const STEPS = [
  {
    n: '01',
    icon: Building2,
    title: 'Coletamos os dados',
    desc: 'Área, localização, padrão construtivo e características do imóvel — tudo organizado num wizard guiado.',
  },
  {
    n: '02',
    icon: BarChart3,
    title: 'Avaliamos qualquer tipo de imóvel',
    desc: '9 categorias cobertas pelo sistema, conforme NBR 14.653 — urbanos, rurais, comerciais e equipamentos.',
  },
  {
    n: '03',
    icon: FileText,
    title: 'Você recebe seu laudo',
    desc: 'PTAM completo em PDF e DOCX editável, com Grau II ou III de fundamentação, pronto para entrega.',
  },
];

// Os 9 tipos de imovel — espelham os componentes 3D em /imoveis3d/.
// Icones Lucide escolhidos para serem visualmente distinguiveis no mobile.
const TIPOS = [
  { icon: Home,      label: 'Residencial Urbano',     accent: false },
  { icon: Building,  label: 'Apartamento',            accent: false },
  { icon: Warehouse, label: 'Galpão Industrial',      accent: false },
  { icon: Store,     label: 'Comércio e Loja',        accent: false },
  { icon: Trees,     label: 'Imóvel Rural',           accent: false },
  { icon: Map,       label: 'Terrenos e Lotes',       accent: true  }, // destaque
  { icon: TreePine,  label: 'Propriedade Rural',      accent: false },
  { icon: Building2, label: 'Sala Comercial',         accent: false },
  { icon: Cog,       label: 'Equipamentos / Garantia',accent: false },
];

export default function Avaliacao3DFallback() {
  return (
    <section
      aria-labelledby="avaliacao3d-fallback-title"
      style={{
        background: 'radial-gradient(ellipse at center, #0a1f18 0%, #050a08 60%, #000000 100%)',
        color: '#fff',
        padding: '80px 24px',
      }}
    >
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {/* === Header === */}
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <span
            style={{
              display: 'inline-block',
              padding: '4px 14px',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              background: 'rgba(201, 168, 76, 0.18)',
              color: '#ffd97a',
              marginBottom: 12,
            }}
          >
            Como funciona em 3 passos
          </span>
          <h2
            id="avaliacao3d-fallback-title"
            style={{ fontSize: 'clamp(24px, 3.5vw, 36px)', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}
          >
            Do imóvel ao PTAM, sem complicação
          </h2>
        </div>

        {/* === 3 passos da narrativa === */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 18,
            marginBottom: 48,
          }}
        >
          {STEPS.map(({ n, icon: Icon, title, desc }) => (
            <div
              key={n}
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 12,
                padding: 24,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  top: 12,
                  right: 16,
                  fontSize: 56,
                  fontWeight: 900,
                  color: 'rgba(201, 168, 76, 0.10)',
                  lineHeight: 1,
                  letterSpacing: '-0.04em',
                }}
              >
                {n}
              </span>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: 10,
                  background: 'rgba(0, 212, 255, 0.10)',
                  border: '1px solid rgba(0, 212, 255, 0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 18,
                }}
              >
                <Icon size={22} color="#00d4ff" strokeWidth={1.6} />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 8px', color: '#fff' }}>{title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.55, margin: 0, color: 'rgba(255, 255, 255, 0.7)' }}>{desc}</p>
            </div>
          ))}
        </div>

        {/* === Grid 3x3 dos 9 tipos de imovel (cena 2 fallback) === */}
        <div
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 14,
            padding: 24,
          }}
        >
          <p
            style={{
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: '#ffd97a',
              margin: '0 0 18px',
              textAlign: 'center',
            }}
          >
            Tipos de imóvel avaliados
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 10,
            }}
          >
            {TIPOS.map(({ icon: Icon, label, accent }) => (
              <div
                key={label}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '16px 8px',
                  background: accent ? 'rgba(201,168,76,0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${accent ? 'rgba(201,168,76,0.35)' : 'rgba(255,255,255,0.06)'}`,
                  borderRadius: 8,
                  textAlign: 'center',
                }}
              >
                <Icon size={26} color={accent ? '#c9a84c' : '#fff'} strokeWidth={1.4} />
                <span
                  style={{
                    fontSize: 11,
                    lineHeight: 1.3,
                    fontWeight: 600,
                    color: accent ? '#ffd97a' : 'rgba(255,255,255,0.85)',
                  }}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
