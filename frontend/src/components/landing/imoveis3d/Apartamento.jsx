// @component Apartamento — icone 3D low-poly de edificio residencial.
// Torre alta em verde marca + 12 janelas em grid emissivas ciano.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#0d4f3c';      // verde primary RomaTec
const COLOR_ROOF = '#1a6b52';      // verde mais claro (terraço)
const COLOR_WINDOW = '#00d4ff';    // ciano emissivo
const COLOR_BASE = '#c9a84c';      // dourado (faixa térrea)

export function Apartamento({ scale = 1, ...props }) {
  const bodyGeo = useMemo(() => new THREE.BoxGeometry(0.6, 1.8, 0.6), []);
  const roofGeo = useMemo(() => new THREE.BoxGeometry(0.66, 0.06, 0.66), []);
  const baseGeo = useMemo(() => new THREE.BoxGeometry(0.7, 0.12, 0.7), []);
  const windowGeo = useMemo(() => new THREE.PlaneGeometry(0.1, 0.14), []);

  // Grid de janelas: 4 andares x 3 colunas em cada face frontal/lateral.
  // Total visivel: ~12 (frontal) + 12 (lateral) — mas so renderizamos as
  // visiveis pra economizar (frontal e direita).
  const janelas = useMemo(() => {
    const arr = [];
    const cols = 3;
    const rows = 4;
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const x = (c - 1) * 0.18;
        const y = -0.62 + r * 0.42;
        // Frontal
        arr.push({ pos: [x, y, 0.301], rot: [0, 0, 0], key: `f-${r}-${c}` });
        // Lateral direita
        arr.push({ pos: [0.301, y, x], rot: [0, Math.PI / 2, 0], key: `r-${r}-${c}` });
      }
    }
    return arr;
  }, []);

  return (
    <group {...props} scale={scale}>
      {/* Base terrea dourada */}
      <mesh geometry={baseGeo} position={[0, -0.95, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BASE} metalness={0.55} roughness={0.35} />
      </mesh>

      {/* Corpo principal */}
      <mesh geometry={bodyGeo} position={[0, 0, 0]} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BODY} metalness={0.7} roughness={0.35} />
      </mesh>

      {/* Cobertura/terraco */}
      <mesh geometry={roofGeo} position={[0, 0.93, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_ROOF} metalness={0.6} roughness={0.4} />
      </mesh>

      {/* Janelas em grid (frontal + lateral direita) */}
      {janelas.map((j) => (
        <mesh key={j.key} geometry={windowGeo} position={j.pos} rotation={j.rot} frustumCulled>
          <meshStandardMaterial
            color={COLOR_WINDOW}
            emissive={COLOR_WINDOW}
            emissiveIntensity={0.55}
            metalness={0.2}
            roughness={0.15}
          />
        </mesh>
      ))}
    </group>
  );
}

export default Apartamento;
