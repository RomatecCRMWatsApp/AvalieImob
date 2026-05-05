// @component CasaResidencial — icone 3D low-poly de casa residencial urbana.
// Corpo cubico branco perolado + telhado em pico dourado + chamine.
// Props: scale, e qualquer prop de <group> (position, rotation, etc).
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#f5f5f0';      // branco perolado
const COLOR_ROOF = '#c9a84c';      // dourado (accent da marca)
const COLOR_DOOR = '#0d4f3c';      // verde primary
const COLOR_WINDOW = '#00d4ff';    // ciano detalhe

export function CasaResidencial({ scale = 1, ...props }) {
  // useMemo: geometrias compartilhaveis evitam recriar em cada render
  const bodyGeo = useMemo(() => new THREE.BoxGeometry(1, 0.7, 1), []);
  const roofGeo = useMemo(() => {
    // ConeGeometry com 4 lados = piramide. Rotacao 45deg pra alinhar com o cubo.
    const geo = new THREE.ConeGeometry(0.78, 0.55, 4);
    return geo;
  }, []);
  const chimneyGeo = useMemo(() => new THREE.BoxGeometry(0.14, 0.32, 0.14), []);
  const doorGeo = useMemo(() => new THREE.PlaneGeometry(0.22, 0.42), []);
  const windowGeo = useMemo(() => new THREE.PlaneGeometry(0.18, 0.18), []);

  return (
    <group {...props} scale={scale}>
      {/* Corpo */}
      <mesh geometry={bodyGeo} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BODY} metalness={0.3} roughness={0.4} />
      </mesh>

      {/* Telhado em pico (piramide rotacionada) */}
      <mesh geometry={roofGeo} position={[0, 0.625, 0]} rotation={[0, Math.PI / 4, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_ROOF} metalness={0.5} roughness={0.3} />
      </mesh>

      {/* Chamine */}
      <mesh geometry={chimneyGeo} position={[0.25, 0.7, -0.15]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BODY} metalness={0.3} roughness={0.4} />
      </mesh>

      {/* Porta frontal (verde marca) */}
      <mesh geometry={doorGeo} position={[0, -0.14, 0.501]} frustumCulled>
        <meshStandardMaterial color={COLOR_DOOR} metalness={0.4} roughness={0.35} />
      </mesh>

      {/* 2 janelas frontais (ciano emissivo) */}
      <mesh geometry={windowGeo} position={[-0.3, 0.05, 0.501]} frustumCulled>
        <meshStandardMaterial color={COLOR_WINDOW} emissive={COLOR_WINDOW} emissiveIntensity={0.6} metalness={0.3} roughness={0.2} />
      </mesh>
      <mesh geometry={windowGeo} position={[0.3, 0.05, 0.501]} frustumCulled>
        <meshStandardMaterial color={COLOR_WINDOW} emissive={COLOR_WINDOW} emissiveIntensity={0.6} metalness={0.3} roughness={0.2} />
      </mesh>
    </group>
  );
}

export default CasaResidencial;
