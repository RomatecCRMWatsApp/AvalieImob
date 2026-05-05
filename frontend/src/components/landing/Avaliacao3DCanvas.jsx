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
import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, Float } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useScrollProgress } from './useScrollProgress';
import {
  CasaResidencial, Apartamento, Galpao, Comercio, Sitio,
  Terreno, Fazenda, SalaComercial, Equipamento,
  TIPOS_IMOVEIS_META,
} from './imoveis3d';

// === CORES DA MARCA ===
const COLOR_PRIMARY = '#0d4f3c';   // derivado de hsl(155, 68%, 18%)
const COLOR_PRIMARY_LIGHT = '#1a6b52';
const COLOR_ACCENT = '#c9a84c';    // derivado de hsl(43, 65%, 52%)
const COLOR_CYAN_DETAIL = '#00d4ff'; // ciano so como detalhe / luz futurista
const COLOR_BG_DARK = '#050a08';   // mais escuro pra harmonizar com gradient

// === SCALES dos icones do grid 3x3 (cena 2 v2) ===
// Normalizacao visual: alguns icones sao maiores que outros por natureza
// (SalaComercial 2.0 alto, Terreno 1.4 plano). Aqui a gente equaliza.
// Constante exposta no topo conforme pedido pra fácil tunning futuro.
const ICON_SCALES = {
  CasaResidencial: 1.0,
  Apartamento:     0.7,
  Galpao:          0.85,
  Comercio:        1.0,
  Sitio:           0.9,
  Terreno:         1.1,
  Fazenda:         0.85,
  SalaComercial:   0.65,
  Equipamento:     1.0,
};

// === DEVICE FRACO === reduz ícones de 9 -> 6 quando dispositivo é low-end.
// Corre uma vez no client. Em SSR/Node retorna false (assume desktop).
function isLowEndDevice() {
  if (typeof window === 'undefined') return false;
  const dpr = window.devicePixelRatio || 1;
  const cores = navigator.hardwareConcurrency || 4;
  return dpr < 2 && cores < 4;
}

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

// === CENA 2 v2 === Vitrine 3D dos 9 tipos de imovel avaliados.
// 3 sub-fases controladas pelo progress global (0.33..0.66 mapeado em 0..1):
//   A) entrada dispersa (raio 6-8, posicoes aleatorias com delay escalonado)
//   B) grid 3x3 frontal organizado (col x row centrados)
//   C) formacao esferica orbital (Fibonacci sphere) com group rotation Y
function Cena2VitrineImoveis({ progress, lowEnd }) {
  const groupRef = useRef();

  // Componentes por ordem canonica do TIPOS_IMOVEIS_META
  const COMPS_FULL = useMemo(() => [
    { Comp: CasaResidencial, scale: ICON_SCALES.CasaResidencial, key: 'casa' },
    { Comp: Apartamento,     scale: ICON_SCALES.Apartamento,     key: 'apto' },
    { Comp: Galpao,          scale: ICON_SCALES.Galpao,          key: 'galpao' },
    { Comp: Comercio,        scale: ICON_SCALES.Comercio,        key: 'comercio' },
    { Comp: Sitio,           scale: ICON_SCALES.Sitio,           key: 'sitio' },
    { Comp: Terreno,         scale: ICON_SCALES.Terreno,         key: 'terreno' },
    { Comp: Fazenda,         scale: ICON_SCALES.Fazenda,         key: 'fazenda' },
    { Comp: SalaComercial,   scale: ICON_SCALES.SalaComercial,   key: 'sala' },
    { Comp: Equipamento,     scale: ICON_SCALES.Equipamento,     key: 'equipamento' },
  ], []);

  // Em devices fracos, mostra so 6 (drop apartamento, fazenda, sala — visualmente
  // mais pesados e tem CasaResidencial / Sitio cobrindo conceitos similares)
  const COMPS = useMemo(() => (lowEnd ? COMPS_FULL.filter((_, i) => ![1, 6, 7].includes(i)) : COMPS_FULL), [COMPS_FULL, lowEnd]);

  // === POSICOES PRE-COMPUTADAS POR SUB-FASE ===
  // A) DISPERSAS: aleatorias com seed deterministica via index
  const posDispersas = useMemo(() => COMPS.map((_, i) => {
    // Seeds pseudo-aleatorias deterministicas (i*PI, i*GoldenRatio, etc)
    const a = (i * 1.732) % (Math.PI * 2);
    const b = (i * 2.236) % (Math.PI * 2);
    const r = 6.5 + (i % 3) * 0.8;
    return [
      Math.cos(a) * r,
      Math.sin(b) * 3,
      Math.sin(a) * r * 0.6,
    ];
  }), [COMPS]);

  // B) GRID 3X3 FRONTAL (ou 3x2 / 2x3 quando 6 icones)
  const posGrid = useMemo(() => {
    const cols = COMPS.length === 9 ? 3 : 3;
    const gap = 2.4;
    return COMPS.map((_, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const totalRows = Math.ceil(COMPS.length / cols);
      return [
        (col - (cols - 1) / 2) * gap,
        ((totalRows - 1) / 2 - row) * gap,
        0,
      ];
    });
  }, [COMPS]);

  // C) FORMACAO ESFERICA ORBITAL (Fibonacci sphere distribution)
  const posEsfera = useMemo(() => {
    const r = 3.4;
    const N = COMPS.length;
    const phi0 = Math.PI * (1 + Math.sqrt(5)); // golden angle
    return COMPS.map((_, i) => {
      const phi = Math.acos(1 - (2 * (i + 0.5)) / N);
      const theta = phi0 * (i + 0.5);
      return [
        r * Math.cos(theta) * Math.sin(phi),
        r * Math.sin(theta) * Math.sin(phi),
        r * Math.cos(phi),
      ];
    });
  }, [COMPS]);

  // Refs por icone pra anim individual (lerp de posicao)
  const itemRefs = useRef([]);
  // Inicializa refs (uma por componente)
  if (itemRefs.current.length !== COMPS.length) {
    itemRefs.current = Array.from({ length: COMPS.length }, () => React.createRef());
  }

  useFrame(() => {
    if (!groupRef.current) return;
    // Visibilidade da cena 2: fade-in 0.30..0.40, fade-out 0.62..0.72
    const fadeIn = sceneRange(progress, 0.30, 0.40);
    const fadeOut = 1 - sceneRange(progress, 0.62, 0.72);
    const visibility = Math.min(fadeIn, fadeOut);
    groupRef.current.scale.setScalar(lerp(groupRef.current.scale.x, visibility, 0.1));

    // Sub-fase: 0..1 dentro de 0.33..0.66
    const subT = sceneRange(progress, 0.33, 0.66);

    // Determinar pesos das 3 sub-fases (cross-fade entre A->B e B->C)
    // A) 0.00..0.33 -> peso 1..0
    // B) 0.33..0.66 -> peso 0..1..0
    // C) 0.66..1.00 -> peso 0..1
    const wA = 1 - smoothstep(subT, 0.0, 0.40);
    const wC = smoothstep(subT, 0.55, 0.95);
    const wB = Math.max(0, 1 - wA - wC);

    // Atualiza posicao de cada icone como blend dos 3 alvos
    COMPS.forEach((_, i) => {
      const ref = itemRefs.current[i];
      if (!ref?.current) return;
      const a = posDispersas[i];
      const b = posGrid[i];
      const c = posEsfera[i];
      const tx = a[0] * wA + b[0] * wB + c[0] * wC;
      const ty = a[1] * wA + b[1] * wB + c[1] * wC;
      const tz = a[2] * wA + b[2] * wB + c[2] * wC;
      // Lerp suave em vez de set direto
      ref.current.position.x = lerp(ref.current.position.x, tx, 0.12);
      ref.current.position.y = lerp(ref.current.position.y, ty, 0.12);
      ref.current.position.z = lerp(ref.current.position.z, tz, 0.12);
      // Rotacao Y de cada item (mais intenso na sub-fase C)
      ref.current.rotation.y += 0.005 + 0.015 * wC;
    });

    // Rotacao Y do grupo pai (so na sub-fase C, "orbita")
    groupRef.current.rotation.y = lerp(groupRef.current.rotation.y, wC * Math.PI * 0.5, 0.05);
  });

  return (
    <group ref={groupRef} scale={0}>
      {COMPS.map((item, i) => {
        const Comp = item.Comp;
        return (
          <group key={item.key} ref={itemRefs.current[i]} position={posDispersas[i]}>
            <Float speed={1.4} rotationIntensity={0.15} floatIntensity={0.3}>
              <Comp scale={item.scale} />
            </Float>
          </group>
        );
      })}
    </group>
  );
}

// Helper: smoothstep classico (interpolacao S-shaped entre edge0 e edge1)
function smoothstep(x, edge0, edge1) {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
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

function Scene({ progress, lowEnd }) {
  const sceneActive = progress > 0.02 && progress < 0.98;
  return (
    <>
      <fog attach="fog" args={[COLOR_BG_DARK, 9, 26]} />
      <color attach="background" args={[COLOR_BG_DARK]} />

      {/* Iluminacao reforcada (cena 2 v2 tem 9 objetos detalhados) */}
      <ambientLight intensity={0.25} />
      <directionalLight position={[5, 8, 5]} intensity={1.5} color={'#ffffff'} castShadow />
      <pointLight position={[-4, 3, -4]} intensity={1.8} color={COLOR_ACCENT} />
      <pointLight position={[ 4, -2, 4]} intensity={1.2} color={COLOR_CYAN_DETAIL} />
      <pointLight position={[ 0,  5, 0]} intensity={0.8} color={COLOR_PRIMARY} />

      <Cena1PlantaBaixa progress={progress} sceneActive={sceneActive} />
      <Cena2VitrineImoveis progress={progress} lowEnd={lowEnd} />
      <Cena3Documento progress={progress} />

      {/* Pos-processamento: Bloom + Vignette pra vibe cinematografica */}
      <EffectComposer multisampling={0} disableNormalPass>
        <Bloom intensity={0.7} luminanceThreshold={0.4} luminanceSmoothing={0.85} mipmapBlur />
        <Vignette offset={0.15} darkness={0.55} />
      </EffectComposer>
    </>
  );
}

// === OVERLAY DE TEXTO ===
// Cena 2 agora tem subtitulo dinamico por sub-fase (A: dispersa, B: grid, C: orbita)
const OVERLAYS = [
  {
    n: '01',
    title: 'Coletamos os dados',
    desc: 'Área, localização, padrão construtivo e características do imóvel — tudo organizado num wizard guiado.',
  },
  {
    n: '02',
    title: 'Avaliamos qualquer tipo de imóvel',
    descs: [
      'Urbanos, rurais, residenciais, comerciais...', // sub-fase A
      '9 categorias cobertas pelo sistema, conforme NBR 14.653.', // sub-fase B
      'Análise especializada para cada perfil de imóvel.', // sub-fase C
    ],
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

// Retorna 0 (A), 1 (B) ou 2 (C) conforme posicao dentro de 0.33..0.66
function getSubFase(p) {
  if (p < 0.33 || p >= 0.66) return 1; // fallback grid
  const t = (p - 0.33) / (0.66 - 0.33);
  if (t < 0.32) return 0;
  if (t < 0.66) return 1;
  return 2;
}

export default function Avaliacao3DCanvas({ onSkip }) {
  const sectionRef = useRef(null);
  const progress = useScrollProgress(sectionRef);
  const cena = getActiveCena(progress);
  const [lowEnd, setLowEnd] = useState(false);

  // GSAP ScrollTrigger registrado dentro do useEffect (evita SSR/hydration issues)
  useEffect(() => {
    setLowEnd(isLowEndDevice());
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

  // Subtitulo dinamico da cena 2 (cross-fade entre as 3 sub-fases via state derivado)
  const cena2Sub = cena === 1 ? OVERLAYS[1].descs[getSubFase(progress)] : null;
  const overlayDesc = cena === 1 ? cena2Sub : OVERLAYS[cena].desc;

  return (
    <section
      ref={sectionRef}
      aria-label="Como funciona a avaliação imobiliária — visualização 3D"
      style={{
        position: 'relative',
        height: '300vh',
        // Background gradient esverdeado (mais cinematografico que cor solida)
        background: 'radial-gradient(ellipse at center, #0a1f18 0%, #050a08 60%, #000000 100%)',
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

        {/* Canvas 3D — camera mais cinematografica (fov 38, position [0,0,9]) */}
        <Canvas
          camera={{ position: [0, 0, 9], fov: 38 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
          style={{ position: 'absolute', inset: 0 }}
          shadows
        >
          <Suspense fallback={null}>
            <Scene progress={progress} lowEnd={lowEnd} />
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
                {overlayDesc}
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
