// @component Sitio — icone 3D low-poly de sitio / pequena propriedade rural.
// Substitui o antigo Rural.jsx. Mudanca conceitual chave: agora alem da
// casinha + 2 silos, tem 4 canteiros plantados (lavoura) — comunica
// "imovel rural produtivo" sem ambiguidade vs Fazenda (que tem cerca).
//
// Renomeado em v2 conforme feedback do CEO: label "Sitio / Pequena
// Propriedade", removendo overlap conceitual com Fazenda (Grande Propriedade).
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_HOUSE = '#f5f5f0';     // branco perolado
const COLOR_ROOF = '#c9a84c';      // dourado
const COLOR_SILO = '#d8d4c5';      // bege metalico
const COLOR_SILO_TOP = '#888';     // cinza metalico
const COLOR_GROUND = '#3d6a4d';    // verde grama (mais claro pra contraste com canteiros)
const COLOR_SOIL = '#5a3a20';      // marrom canteiros (terra arada)
const COLOR_CROP = '#7fb069';      // verde claro plantacao (linhas de cultivo)

export function Sitio({ scale = 1, ...props }) {
  const groundGeo = useMemo(() => new THREE.BoxGeometry(1.7, 0.08, 1.7), []);
  const houseGeo = useMemo(() => new THREE.BoxGeometry(0.5, 0.4, 0.45), []);
  const houseRoofGeo = useMemo(() => new THREE.ConeGeometry(0.38, 0.28, 4), []);
  const siloBodyGeo = useMemo(() => new THREE.CylinderGeometry(0.16, 0.16, 0.95, 16), []);
  const siloTopGeo = useMemo(() => new THREE.SphereGeometry(0.16, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), []);
  const doorGeo = useMemo(() => new THREE.PlaneGeometry(0.13, 0.24), []);

  // Canteiros: BoxGeometry baixinha = canteiro de terra arada.
  // 4 canteiros (2x2) representando lavoura no lado direito do sitio.
  const canteiroBaseGeo = useMemo(() => new THREE.BoxGeometry(0.35, 0.04, 0.5), []);
  // Linhas de cultivo: tiras finas verdes claras dentro de cada canteiro.
  const cropLineGeo = useMemo(() => new THREE.BoxGeometry(0.32, 0.05, 0.04), []);

  const canteiros = useMemo(() => [
    { x:  0.15, z:  0.55 },
    { x:  0.55, z:  0.55 },
    { x:  0.15, z: -0.10 },
    { x:  0.55, z: -0.10 },
  ], []);

  return (
    <group {...props} scale={scale}>
      {/* Chao verde grama */}
      <mesh geometry={groundGeo} position={[0, -0.55, 0]} receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_GROUND} metalness={0.1} roughness={0.85} />
      </mesh>

      {/* Casa pequena (esquerda-frente) */}
      <group position={[-0.45, -0.31, 0.2]}>
        <mesh geometry={houseGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_HOUSE} metalness={0.3} roughness={0.45} />
        </mesh>
        <mesh geometry={houseRoofGeo} position={[0, 0.32, 0]} rotation={[0, Math.PI / 4, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_ROOF} metalness={0.5} roughness={0.35} />
        </mesh>
        <mesh geometry={doorGeo} position={[0, -0.08, 0.226]} frustumCulled>
          <meshStandardMaterial color="#5a3a20" metalness={0.3} roughness={0.5} />
        </mesh>
      </group>

      {/* 2 silos (esquerda-fundo, atras da casa) */}
      <group position={[-0.55, 0.0, -0.4]}>
        <mesh geometry={siloBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO} metalness={0.7} roughness={0.3} />
        </mesh>
        <mesh geometry={siloTopGeo} position={[0, 0.475, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO_TOP} metalness={0.85} roughness={0.25} />
        </mesh>
      </group>
      <group position={[-0.2, -0.05, -0.5]} scale={0.85}>
        <mesh geometry={siloBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO} metalness={0.7} roughness={0.3} />
        </mesh>
        <mesh geometry={siloTopGeo} position={[0, 0.475, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_SILO_TOP} metalness={0.85} roughness={0.25} />
        </mesh>
      </group>

      {/* === LAVOURA: 4 canteiros plantados (lado direito) === */}
      {canteiros.map((c, i) => (
        <group key={`canteiro-${i}`} position={[c.x, -0.49, c.z]}>
          {/* Solo arado marrom */}
          <mesh geometry={canteiroBaseGeo} receiveShadow frustumCulled>
            <meshStandardMaterial color={COLOR_SOIL} metalness={0.15} roughness={0.85} />
          </mesh>
          {/* 4 linhas de cultivo verde claro alternadas dentro do canteiro */}
          {[-0.18, -0.06, 0.06, 0.18].map((zOffset, j) => (
            <mesh
              key={`crop-${i}-${j}`}
              geometry={cropLineGeo}
              position={[0, 0.045, zOffset]}
              frustumCulled
            >
              <meshStandardMaterial color={COLOR_CROP} metalness={0.1} roughness={0.7} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

export default Sitio;
