// @component Rural — icone 3D low-poly de sitio/imovel rural pequeno.
// Casinha simples (cubo + telhado) + 2 silos cilindricos + chao verde grama.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_HOUSE = '#f5f5f0';     // branco perolado
const COLOR_ROOF = '#c9a84c';      // dourado (telhado da casa)
const COLOR_SILO = '#d8d4c5';      // bege metalico
const COLOR_SILO_TOP = '#888';     // cinza metalico (cupula)
const COLOR_GROUND = '#2d5a3d';    // verde grama escuro

export function Rural({ scale = 1, ...props }) {
  const groundGeo = useMemo(() => new THREE.BoxGeometry(1.7, 0.08, 1.7), []);
  const houseGeo = useMemo(() => new THREE.BoxGeometry(0.55, 0.45, 0.5), []);
  const houseRoofGeo = useMemo(() => new THREE.ConeGeometry(0.42, 0.32, 4), []);
  const siloBodyGeo = useMemo(() => new THREE.CylinderGeometry(0.18, 0.18, 1.1, 16), []);
  const siloTopGeo = useMemo(() => new THREE.SphereGeometry(0.18, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), []);
  const doorGeo = useMemo(() => new THREE.PlaneGeometry(0.14, 0.26), []);

  return (
    <group {...props} scale={scale}>
      {/* Chao verde grama */}
      <mesh geometry={groundGeo} position={[0, -0.55, 0]} receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_GROUND} metalness={0.1} roughness={0.8} />
      </mesh>

      {/* Casa pequena (esquerda) */}
      <group position={[-0.4, -0.28, 0.2]}>
        <mesh geometry={houseGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_HOUSE} metalness={0.3} roughness={0.45} />
        </mesh>
        <mesh geometry={houseRoofGeo} position={[0, 0.36, 0]} rotation={[0, Math.PI / 4, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_ROOF} metalness={0.5} roughness={0.35} />
        </mesh>
        <mesh geometry={doorGeo} position={[0, -0.085, 0.251]} frustumCulled>
          <meshStandardMaterial color="#5a3a20" metalness={0.3} roughness={0.5} />
        </mesh>
      </group>

      {/* Silo 1 (direita-frente) */}
      <group position={[0.35, 0.05, 0.25]}>
        <mesh geometry={siloBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO} metalness={0.7} roughness={0.3} />
        </mesh>
        <mesh geometry={siloTopGeo} position={[0, 0.55, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO_TOP} metalness={0.85} roughness={0.25} />
        </mesh>
      </group>

      {/* Silo 2 (direita-fundo, ligeiramente menor) */}
      <group position={[0.6, -0.05, -0.2]} scale={0.85}>
        <mesh geometry={siloBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO} metalness={0.7} roughness={0.3} />
        </mesh>
        <mesh geometry={siloTopGeo} position={[0, 0.55, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO_TOP} metalness={0.85} roughness={0.25} />
        </mesh>
      </group>
    </group>
  );
}

export default Rural;
