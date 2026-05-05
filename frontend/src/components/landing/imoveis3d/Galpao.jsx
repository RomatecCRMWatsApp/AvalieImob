// @component Galpao — icone 3D low-poly de galpao industrial.
// Corpo largo e baixo + telhado abobadado (meio-cilindro) + portao dourado.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#888888';      // cinza metalico
const COLOR_ROOF = '#666666';      // cinza mais escuro
const COLOR_DOOR = '#c9a84c';      // dourado (portao grande)
const COLOR_TRIM = '#0d4f3c';      // verde marca (faixa horizontal)

export function Galpao({ scale = 1, ...props }) {
  const bodyGeo = useMemo(() => new THREE.BoxGeometry(1.6, 0.5, 1), []);
  // Telhado abobadado: meio-cilindro (thetaLength = PI). CylinderGeometry com
  // openEnded = false fica fechado nos lados — mais limpo visualmente.
  const roofGeo = useMemo(() => {
    const geo = new THREE.CylinderGeometry(0.55, 0.55, 1.6, 16, 1, false, 0, Math.PI);
    geo.rotateZ(Math.PI / 2);
    return geo;
  }, []);
  const doorGeo = useMemo(() => new THREE.PlaneGeometry(0.55, 0.4), []);
  const trimGeo = useMemo(() => new THREE.BoxGeometry(1.61, 0.04, 1.01), []);

  return (
    <group {...props} scale={scale}>
      {/* Corpo */}
      <mesh geometry={bodyGeo} position={[0, 0, 0]} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BODY} metalness={0.85} roughness={0.3} />
      </mesh>

      {/* Faixa horizontal verde (decoracao no meio do corpo) */}
      <mesh geometry={trimGeo} position={[0, 0.1, 0]} frustumCulled>
        <meshStandardMaterial color={COLOR_TRIM} metalness={0.5} roughness={0.4} />
      </mesh>

      {/* Telhado abobadado */}
      <mesh geometry={roofGeo} position={[0, 0.27, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_ROOF} metalness={0.9} roughness={0.25} side={THREE.DoubleSide} />
      </mesh>

      {/* Portao grande frontal */}
      <mesh geometry={doorGeo} position={[0, -0.05, 0.501]} frustumCulled>
        <meshStandardMaterial color={COLOR_DOOR} metalness={0.7} roughness={0.3} emissive={COLOR_DOOR} emissiveIntensity={0.1} />
      </mesh>

      {/* Linhas verticais do portao (efeito de portas industriais corredicas) */}
      {[-0.18, -0.06, 0.06, 0.18].map((x) => (
        <mesh key={`bar-${x}`} position={[x, -0.05, 0.502]} frustumCulled>
          <planeGeometry args={[0.012, 0.4]} />
          <meshStandardMaterial color={COLOR_BODY} metalness={0.9} roughness={0.2} />
        </mesh>
      ))}
    </group>
  );
}

export default Galpao;
