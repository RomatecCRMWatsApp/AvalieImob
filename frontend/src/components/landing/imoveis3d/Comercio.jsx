// @component Comercio — icone 3D low-poly de loja/estabelecimento comercial.
// Corpo + vitrine frontal grande emissiva + toldo dourado triangular + placa.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#e8e4d8';      // bege creme
const COLOR_VITRINE = '#00d4ff';   // ciano (vitrine iluminada)
const COLOR_TOLDO = '#c9a84c';     // dourado (toldo)
const COLOR_PLACA = '#0d4f3c';     // verde marca (placa)
const COLOR_DOOR = '#444';

export function Comercio({ scale = 1, ...props }) {
  const bodyGeo = useMemo(() => new THREE.BoxGeometry(1, 0.9, 0.7), []);
  const vitrineGeo = useMemo(() => new THREE.PlaneGeometry(0.78, 0.45), []);
  // Toldo: prisma triangular saliente. Usamos ConeGeometry com 3 lados rotacionada.
  const toldoGeo = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(-0.5, 0);
    shape.lineTo(0.5, 0);
    shape.lineTo(0, -0.2);
    shape.closePath();
    return new THREE.ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: false });
  }, []);
  const placaGeo = useMemo(() => new THREE.BoxGeometry(0.85, 0.18, 0.05), []);
  const doorGeo = useMemo(() => new THREE.PlaneGeometry(0.16, 0.35), []);

  return (
    <group {...props} scale={scale}>
      {/* Corpo */}
      <mesh geometry={bodyGeo} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BODY} metalness={0.3} roughness={0.45} />
      </mesh>

      {/* Vitrine frontal grande (emissiva ciano) */}
      <mesh geometry={vitrineGeo} position={[0, -0.05, 0.351]} frustumCulled>
        <meshStandardMaterial
          color={COLOR_VITRINE}
          emissive={COLOR_VITRINE}
          emissiveIntensity={0.8}
          metalness={0.2}
          roughness={0.1}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* Porta lateral */}
      <mesh geometry={doorGeo} position={[0.32, -0.275, 0.351]} frustumCulled>
        <meshStandardMaterial color={COLOR_DOOR} metalness={0.4} roughness={0.4} />
      </mesh>

      {/* Toldo (prisma triangular saliente) */}
      <mesh
        geometry={toldoGeo}
        position={[0, 0.22, 0.35]}
        rotation={[Math.PI / 2, 0, 0]}
        castShadow
        frustumCulled
      >
        <meshStandardMaterial color={COLOR_TOLDO} metalness={0.55} roughness={0.35} />
      </mesh>

      {/* Placa retangular acima da vitrine */}
      <mesh geometry={placaGeo} position={[0, 0.42, 0.36]} castShadow frustumCulled>
        <meshStandardMaterial
          color={COLOR_PLACA}
          metalness={0.5}
          roughness={0.4}
          emissive={COLOR_PLACA}
          emissiveIntensity={0.18}
        />
      </mesh>
    </group>
  );
}

export default Comercio;
