// @component SalaComercial — icone 3D low-poly de torre/edificio comercial.
// Torre fina e alta + faixas horizontais de janelas + antena/mastro no topo.
// Material vidro escuro semi-translucido pra "vibe corporativa".
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#1a3d2e';      // verde-vidro escuro
const COLOR_FRAME = '#0d4f3c';     // verde marca (estrutura)
const COLOR_GLASS = '#00d4ff';     // ciano (faixas de vidro)
const COLOR_TOP = '#c9a84c';       // dourado (antena)
const COLOR_ANTENNA = '#888';

export function SalaComercial({ scale = 1, ...props }) {
  const bodyGeo = useMemo(() => new THREE.BoxGeometry(0.5, 2, 0.5), []);
  const frameGeo = useMemo(() => new THREE.BoxGeometry(0.55, 0.06, 0.55), []);
  const baseGeo = useMemo(() => new THREE.BoxGeometry(0.65, 0.1, 0.65), []);
  // Faixas horizontais de janelas (5 andares, cobrindo as 4 faces)
  const stripGeo = useMemo(() => new THREE.BoxGeometry(0.502, 0.18, 0.502), []);
  const antennaGeo = useMemo(() => new THREE.CylinderGeometry(0.012, 0.012, 0.45, 8), []);
  const antennaTopGeo = useMemo(() => new THREE.SphereGeometry(0.03, 12, 12), []);

  // Y das 5 faixas de janelas (distribuidas ao longo da torre)
  const strips = useMemo(() => [-0.7, -0.32, 0.06, 0.44, 0.82], []);

  return (
    <group {...props} scale={scale}>
      {/* Base solida dourada */}
      <mesh geometry={baseGeo} position={[0, -1.05, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_TOP} metalness={0.7} roughness={0.3} />
      </mesh>

      {/* Corpo principal (vidro escuro, semi-transparente) */}
      <mesh geometry={bodyGeo} position={[0, 0, 0]} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial
          color={COLOR_BODY}
          metalness={0.85}
          roughness={0.2}
          transparent
          opacity={0.75}
        />
      </mesh>

      {/* 5 faixas de janelas ciano (envolvendo a torre) */}
      {strips.map((y, i) => (
        <mesh key={`strip-${i}`} geometry={stripGeo} position={[0, y, 0]} frustumCulled>
          <meshStandardMaterial
            color={COLOR_GLASS}
            emissive={COLOR_GLASS}
            emissiveIntensity={0.45}
            metalness={0.4}
            roughness={0.15}
            transparent
            opacity={0.9}
          />
        </mesh>
      ))}

      {/* Frames horizontais entre as faixas (estrutura) */}
      {[-0.5, -0.12, 0.26, 0.64].map((y, i) => (
        <mesh key={`frame-${i}`} geometry={frameGeo} position={[0, y, 0]} frustumCulled>
          <meshStandardMaterial color={COLOR_FRAME} metalness={0.6} roughness={0.4} />
        </mesh>
      ))}

      {/* Topo da torre (cobertura solida) */}
      <mesh geometry={frameGeo} position={[0, 1.03, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_FRAME} metalness={0.6} roughness={0.4} />
      </mesh>

      {/* Antena/mastro no topo */}
      <mesh geometry={antennaGeo} position={[0, 1.29, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_ANTENNA} metalness={0.95} roughness={0.15} />
      </mesh>

      {/* Bola dourada no topo da antena */}
      <mesh geometry={antennaTopGeo} position={[0, 1.53, 0]} frustumCulled>
        <meshStandardMaterial
          color={COLOR_TOP}
          metalness={0.85}
          roughness={0.2}
          emissive={COLOR_TOP}
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  );
}

export default SalaComercial;
