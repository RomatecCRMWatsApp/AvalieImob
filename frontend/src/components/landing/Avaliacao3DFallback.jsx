// @component Avaliacao3DFallback — versao estatica da secao 3D para mobile
// (<768px) e usuarios com prefers-reduced-motion. Mostra os mesmos 3 passos
// do Canvas R3F como cards lado-a-lado (desktop) ou empilhados (mobile),
// com icones Lucide e estetica coerente com a landing.
import React from 'react';
import { Building2, BarChart3, FileText } from 'lucide-react';

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
    title: 'Cruzamos com o mercado',
    desc: 'Análise estatística conforme NBR 14.653 com amostras de imóveis comparáveis e tratamento Chauvenet.',
  },
  {
    n: '03',
    icon: FileText,
    title: 'Você recebe seu laudo',
    desc: 'PTAM completo em PDF e DOCX editável, com Grau II ou III de fundamentação, pronto para entrega.',
  },
];

export default function Avaliacao3DFallback() {
  return (
    <section
      aria-labelledby="avaliacao3d-fallback-title"
      style={{
        background: 'linear-gradient(180deg, #0a0f0a 0%, #0d1f17 100%)',
        color: '#fff',
        padding: '80px 24px',
      }}
    >
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
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

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 18,
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
      </div>
    </section>
  );
}
