// @component Avaliacao3DCanvas — Canvas R3F pesado da secao "Do imovel ao PTAM".
// Carregado via lazy() pelo wrapper Avaliacao3D pra nao penalizar mobile.
//
// 3 cenas controladas pelo progresso de scroll (0..1):
//   CENA 1 (0.00 -> 0.33): Coletamos os dados   — planta baixa wireframe + lights
//   CENA 2 (0.33 -> 0.66): Cruzamos com mercado — casa 3D com comparaveis flutuando
//   CENA 3 (0.66 -> 1.00): Geramos o PTAM       — documento + valor monetario
//
// Cores derivadas do tema da marca (tailwind.config.js + index.css):
//   primary  hsl(155, 68%, 18%)  -> #0d4f3c (verde RomaTec)
//   accent   hsl(43, 65%, 52%)   -> #c9a84c (dourado)
//   ciano #00d4ff usado APENAS como light pontual (vibe futurista, nao dominante)
import React, { Suspense, useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, Float } from '@react-three/drei';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useScrollProgress } from './useScrollProgress';

// === CORES DA MARCA ===
const COLOR_PRIMARY = '#0d4f3c';   // derivado de hsl(155, 68%, 18%)
const COLOR_PRIMARY_LIGHT = '#1a6b52';
const COLOR_ACCENT = '#c9a84c';    // derivado de hsl(43, 65%, 52%)
const COLOR_CYAN_DETAIL = '#00d4ff'; // ciano so como detalhe / luz futurista
const COLOR_BG_DARK = '#0a0f0a';

// Helper: lerp suave
const lerp = (a, b, t) => a + (b - a) * t;

// Mapeia progresso global (0..1) pra progresso de uma cena especifica.
// Ex: sceneRange(p, 0.33, 0.66) -> 0..1 dentro do intervalo.
const sceneRange = (p, start, end) => {
  if (p <= start) return 0;
  if (p >= end) return 1;
  return (p - start) / (end - start);
};

// === CENA 1 === Planta baixa wireframe (cubos baixos representando comodos)
function Cena1PlantaBaixa({ progress, sceneActive }) {
  const groupRef = useRef();
  const lightRef = useRef();

  // Comodos da planta: x, z, w, d (largura/profundidade no plano XZ)
  const comodos = useMemo(
    () => [
      { x: -2.0, z: -1.0, w: 1.8, d: 1.6, key: 'sala' },
      { x: -0.1, z: -1.0, w: 1.6, d: 1.6, key: 'cozinha' },
      { x: 1.6, z: -1.0, w: 1.4, d: 1.6, key: 'varanda' },
      { x: -2.0, z: 0.9, w: 1.4, d: 1.4, key: 'quarto1' },
      { x: -0.4, z: 0.9, w: 1.4, d: 1.4, key: 'quarto2' },
      { x: 1.2, z: 0.9, w: 1.6, d: 1.4, key: 'banho' },
    ],
    []
  );

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    // Cena 1: planta DEITADA (rotateX = -PI/2) e baixa (scaleY pequeno).
    // Cena 2: comeca a se erguer. progress global 0.33..0.66 -> ergue de -PI/2 ate 0.
    const tErguendo = sceneRange(progress, 0.30, 0.55);
    const targetRotX = lerp(-Math.PI / 2, 0, tErguendo);
    const targetScaleY = lerp(0.05, 1, tErguendo);

    groupRef.current.rotation.x = lerp(groupRef.current.rotation.x, targetRotX, 0.1);
    groupRef.current.scale.y = lerp(groupRef.current.scale.y, targetScaleY, 0.1);

    // Rotacao Y suave continua (camera "passeando")
    groupRef.current.rotation.y += delta * 0.08 * (sceneActive ? 1 : 0.3);

    // Luz pontual ciana caminhando pelos comodos na cena 1
    if (lightRef.current) {
      const t = state.clock.elapsedTime;
      const idx = Math.floor(t * 0.7) % comodos.length;
      const target = comodos[idx];
      lightRef.current.position.x = lerp(lightRef.current.position.x, target.x, 0.05);
      lightRef.current.position.z = lerp(lightRef.current.position.z, target.z, 0.05);
      lightRef.current.position.y = 1.5;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Piso/base da planta */}
      <mesh position={[0, -0.05, 0]} receiveShadow>
        <boxGeometry args={[6.5, 0.08, 4.5]} />
        <meshStandardMaterial color={COLOR_PRIMARY} metalness={0.2} roughness={0.7} />
      </mesh>

      {/* Comodos: cubos baixos + edges em ciano */}
      {comodos.map((c) => (
        <group key={c.key} position={[c.x, 0.4, c.z]}>
          <mesh>
            <boxGeometry args={[c.w, 0.8, c.d]} />
            <meshStandardMaterial
              color={COLOR_PRIMARY_LIGHT}
              metalness={0.3}
              roughness={0.5}
              transparent
              opacity={0.35}
            />
          </mesh>
          <lineSegments>
            <edgesGeometry args={[new THREE.BoxGeometry(c.w, 0.8, c.d)]} />
            <lineBasicMaterial color={COLOR_CYAN_DETAIL} linewidth={1} />
          </lineSegments>
        </group>
      ))}

      {/* Luz pontual ciana — viaja pelos comodos */}
      <pointLight ref={lightRef} color={COLOR_CYAN_DETAIL} intensity={3} distance={3} />
    </group>
  );
}

// === CENA 2 === Casa 3D + comparaveis flutuando + linhas de conexao
function Cena2Comparaveis({ progress }) {
  const groupRef = useRef();
  const linesRef = useRef();

  const comparaveis = useMemo(() => {
    const arr = [];
    const N = 24;
    for (let i = 0; i < N; i += 1) {
      const angle = (i / N) * Math.PI * 2;
      const r = 4.5 + Math.random() * 1.8;
      const y = (Math.random() - 0.5) * 2.5;
      arr.push({
        pos: [Math.cos(angle) * r, y, Math.sin(angle) * r],
        size: 0.18 + Math.random() * 0.18,
        delay: Math.random() * Math.PI * 2,
      });
    }
    return arr;
  }, []);

  // Linhas: criadas uma vez, opacity pulsa conforme cena 2 ativa
  const lineGeo = useMemo(() => {
    const positions = [];
    comparaveis.forEach((c) => {
      positions.push(0, 0, 0, c.pos[0], c.pos[1], c.pos[2]);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    return geo;
  }, [comparaveis]);

  useFrame((state) => {
    if (!groupRef.current) return;
    // Cena 2 visivel quando progress entre 0.33 e 0.66 (com fade dos lados)
    const t2 = sceneRange(progress, 0.30, 0.40); // fade-in
    const t2out = 1 - sceneRange(progress, 0.62, 0.75); // fade-out
    const visibility = Math.min(t2, t2out);

    groupRef.current.scale.setScalar(lerp(groupRef.current.scale.x, visibility, 0.1));

    // Comparaveis pulsam levemente
    if (linesRef.current) {
      linesRef.current.material.opacity = lerp(
        linesRef.current.material.opacity,
        visibility * 0.45,
        0.1
      );
    }
  });

  return (
    <group ref={groupRef} scale={0}>
      {/* Linhas do centro pra cada comparavel */}
      <lineSegments ref={linesRef}>
        <primitive object={lineGeo} attach="geometry" />
        <lineBasicMaterial color={COLOR_CYAN_DETAIL} transparent opacity={0} />
      </lineSegments>

      {/* Comparaveis flutuando */}
      {comparaveis.map((c, i) => (
        <Float key={i} speed={1.2} rotationIntensity={0.4} floatIntensity={0.6}>
          <mesh position={c.pos}>
            <boxGeometry args={[c.size, c.size, c.size]} />
            <meshStandardMaterial
              color={COLOR_ACCENT}
              metalness={0.6}
              roughness={0.3}
              emissive={COLOR_ACCENT}
              emissiveIntensity={0.15}
            />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

// === CENA 3 === Documento PTAM + selo dourado + contador R$
function Cena3Documento({ progress }) {
  const docRef = useRef();
  const seloRef = useRef();
  const valorRef = useRef({ atual: 0 });

  // Valor exemplo: R$ 487.000 com contador animado
  const valorAlvo = 487000;

  useFrame(() => {
    if (!docRef.current) return;
    // Cena 3: 0.66 -> 1.0
    const t3 = sceneRange(progress, 0.62, 0.85);
    docRef.current.scale.setScalar(lerp(docRef.current.scale.x, t3, 0.1));
    // Documento "deita" levemente (proporcao A4 vertical)
    docRef.current.rotation.y = lerp(docRef.current.rotation.y, t3 * Math.PI * 0.04, 0.1);

    // Selo PTAM gira lentamente
    if (seloRef.current) {
      seloRef.current.rotation.z += 0.005 * t3;
    }

    // Contador de valor
    valorRef.current.atual = lerp(valorRef.current.atual, valorAlvo * t3, 0.08);
  });

  const valorFmt = () => {
    const v = Math.round(valorRef.current.atual);
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  };

  return (
    <group ref={docRef} scale={0}>
      {/* Documento (proporcao A4 vertical: 1 : 1.414) */}
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[2.4, 3.4]} />
        <meshStandardMaterial color="#f8f6ee" metalness={0.05} roughness={0.85} side={THREE.DoubleSide} />
      </mesh>

      {/* Linhas horizontais simulando texto do laudo */}
      {[1.3, 1.0, 0.7, 0.4, 0.1, -0.2, -0.5, -0.8, -1.1].map((y, i) => (
        <mesh key={i} position={[0, y, 0.005]}>
          <planeGeometry args={[1.9 - (i % 3) * 0.3, 0.04]} />
          <meshBasicMaterial color="#444" />
        </mesh>
      ))}

      {/* Selo PTAM no canto superior direito do documento */}
      <group ref={seloRef} position={[0.85, 1.45, 0.02]}>
        <mesh>
          <circleGeometry args={[0.32, 32]} />
          <meshStandardMaterial
            color={COLOR_ACCENT}
            metalness={0.7}
            roughness={0.25}
            emissive={COLOR_ACCENT}
            emissiveIntensity={0.25}
          />
        </mesh>
        <Html center transform occlude={false} position={[0, 0, 0.01]}>
          <div style={{ color: '#1a1916', fontWeight: 900, fontSize: 11, letterSpacing: '0.08em', pointerEvents: 'none' }}>
            PTAM
          </div>
        </Html>
      </group>

      {/* Valor monetario grande */}
      <Html center transform position={[0, -1.55, 0.02]}>
        <div
          style={{
            color: COLOR_PRIMARY,
            fontWeight: 900,
            fontSize: 28,
            letterSpacing: '-0.02em',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            textShadow: '0 0 12px rgba(201,168,76,0.18)',
          }}
        >
          {valorFmt()}
        </div>
      </Html>
    </group>
  );
}

function Scene({ progress }) {
  const sceneActive = progress > 0.02 && progress < 0.98;
  return (
    <>
      <fog attach="fog" args={[COLOR_BG_DARK, 8, 22]} />
      <color attach="background" args={[COLOR_BG_DARK]} />

      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 8, 5]} intensity={0.8} color={'#ffffff'} castShadow />
      <pointLight position={[-6, 3, 4]} intensity={0.6} color={COLOR_CYAN_DETAIL} />
      <pointLight position={[6, -2, -4]} intensity={0.4} color={COLOR_ACCENT} />

      <Cena1PlantaBaixa progress={progress} sceneActive={sceneActive} />
      <Cena2Comparaveis progress={progress} />
      <Cena3Documento progress={progress} />
    </>
  );
}

// === OVERLAY DE TEXTO ===
const OVERLAYS = [
  {
    n: '01',
    title: 'Coletamos os dados',
    desc: 'Área, localização, padrão construtivo e características do imóvel — tudo organizado num wizard guiado.',
  },
  {
    n: '02',
    title: 'Cruzamos com o mercado',
    desc: 'Análise estatística conforme NBR 14.653 com amostras de imóveis comparáveis e tratamento Chauvenet.',
  },
  {
    n: '03',
    title: 'Você recebe seu laudo',
    desc: 'PTAM completo em PDF e DOCX editável, com Grau II ou III de fundamentação, pronto para entrega.',
  },
];

function getActiveCena(p) {
  if (p < 0.33) return 0;
  if (p < 0.66) return 1;
  return 2;
}

export default function Avaliacao3DCanvas({ onSkip }) {
  const sectionRef = useRef(null);
  const progress = useScrollProgress(sectionRef);
  const cena = getActiveCena(progress);

  // GSAP ScrollTrigger registrado dentro do useEffect (evita SSR/hydration issues)
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    // ScrollTrigger.refresh garante que mudancas de DOM (lazy load do canvas)
    // sejam recalculadas. Isso evita "trigger congelado" caso o componente
    // entre tarde no DOM.
    const t = setTimeout(() => ScrollTrigger.refresh(), 100);
    return () => {
      clearTimeout(t);
      // Limpa todos os triggers criados por este componente (defensivo)
      ScrollTrigger.getAll().forEach((st) => st.kill());
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      aria-label="Como funciona a avaliação imobiliária — visualização 3D"
      style={{
        position: 'relative',
        height: '300vh',
        background: COLOR_BG_DARK,
      }}
    >
      <div style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }}>
        {/* Botao "Pular animacao" — acessibilidade */}
        <button
          onClick={onSkip}
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            zIndex: 10,
            background: 'rgba(255,255,255,0.08)',
            color: 'rgba(255,255,255,0.85)',
            border: '1px solid rgba(255,255,255,0.18)',
            borderRadius: 6,
            padding: '8px 14px',
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            backdropFilter: 'blur(6px)',
          }}
          aria-label="Pular animação 3D e ir direto para o conteúdo"
        >
          Pular animação ↓
        </button>

        {/* Canvas 3D */}
        <Canvas
          camera={{ position: [0, 1.8, 9], fov: 45 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
          style={{ position: 'absolute', inset: 0 }}
        >
          <Suspense fallback={null}>
            <Scene progress={progress} />
          </Suspense>
        </Canvas>

        {/* Overlay de texto */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            pointerEvents: 'none',
            zIndex: 5,
          }}
        >
          <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 32px', width: '100%' }}>
            <div style={{ maxWidth: 460, color: '#fff' }}>
              <span
                style={{
                  display: 'inline-block',
                  fontSize: 80,
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  color: COLOR_ACCENT,
                  lineHeight: 1,
                  textShadow: '0 0 24px rgba(201,168,76,0.3)',
                  marginBottom: 8,
                }}
              >
                {OVERLAYS[cena].n}
              </span>
              <h2
                style={{
                  fontSize: 'clamp(28px, 4vw, 44px)',
                  fontWeight: 800,
                  margin: '0 0 14px',
                  letterSpacing: '-0.02em',
                  lineHeight: 1.1,
                }}
              >
                {OVERLAYS[cena].title}
              </h2>
              <p
                style={{
                  fontSize: 'clamp(14px, 1.5vw, 17px)',
                  lineHeight: 1.6,
                  margin: 0,
                  color: 'rgba(255,255,255,0.78)',
                  maxWidth: 420,
                }}
              >
                {OVERLAYS[cena].desc}
              </p>
            </div>
          </div>
        </div>

        {/* Indicador de progresso lateral (3 dots) */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            right: 28,
            transform: 'translateY(-50%)',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            zIndex: 5,
          }}
          aria-hidden="true"
        >
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: i === cena ? COLOR_ACCENT : 'rgba(255,255,255,0.25)',
                transition: 'background 0.3s ease',
                boxShadow: i === cena ? `0 0 12px ${COLOR_ACCENT}` : 'none',
              }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
