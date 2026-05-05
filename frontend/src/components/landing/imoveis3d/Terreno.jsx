// @component Terreno — icone 3D low-poly de lote/terreno urbano.
// Plano retangular deitado + 4 estacas douradas nos cantos + linhas de
// perimetro tracejadas + marcador "M²" via Html no centro.
import React, { useMemo } from 'react';
import * as THREE from 'three';
import { Text } from '@react-three/drei';

const COLOR_GROUND = '#5a4a3a';    // marrom terra
const COLOR_STAKE = '#c9a84c';     // dourado (estacas)
const COLOR_LINE = '#00d4ff';      // ciano (linhas de perimetro)

export function Terreno({ scale = 1, ...props }) {
  const groundGeo = useMemo(() => new THREE.BoxGeometry(1.4, 0.06, 1.4), []);
  const stakeGeo = useMemo(() => new THREE.CylinderGeometry(0.025, 0.025, 0.45, 8), []);
  const stakeTopGeo = useMemo(() => new THREE.SphereGeometry(0.045, 8, 8), []);

  // Linha de perimetro: BufferGeometry com 4 segmentos conectando os cantos
  const perimeterGeo = useMemo(() => {
    const half = 0.6;
    const y = 0.18;
    const positions = new Float32Array([
      -half, y, -half,  half, y, -half,
       half, y, -half,  half, y,  half,
       half, y,  half, -half, y,  half,
      -half, y,  half, -half, y, -half,
    ]);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  // Posicoes das 4 estacas (cantos)
  const stakes = useMemo(() => [
    { pos: [-0.6, 0.2, -0.6] },
    { pos: [ 0.6, 0.2, -0.6] },
    { pos: [ 0.6, 0.2,  0.6] },
    { pos: [-0.6, 0.2,  0.6] },
  ], []);

  return (
    <group {...props} scale={scale}>
      {/* Plano retangular do terreno (deitado) */}
      <mesh geometry={groundGeo} position={[0, -0.05, 0]} receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_GROUND} metalness={0.2} roughness={0.7} />
      </mesh>

      {/* 4 estacas douradas nos cantos */}
      {stakes.map((s, i) => (
        <group key={`stake-${i}`} position={s.pos}>
          <mesh geometry={stakeGeo} castShadow frustumCulled>
            <meshStandardMaterial color={COLOR_STAKE} metalness={0.7} roughness={0.3} emissive={COLOR_STAKE} emissiveIntensity={0.2} />
          </mesh>
          <mesh geometry={stakeTopGeo} position={[0, 0.24, 0]} frustumCulled>
            <meshStandardMaterial color={COLOR_STAKE} metalness={0.8} roughness={0.2} emissive={COLOR_STAKE} emissiveIntensity={0.4} />
          </mesh>
        </group>
      ))}

      {/* Linhas de perimetro ciano (4 segmentos formando retangulo) */}
      <lineSegments>
        <primitive object={perimeterGeo} attach="geometry" />
        <lineBasicMaterial color={COLOR_LINE} transparent opacity={0.7} linewidth={1} />
      </lineSegments>

      {/* Marcador M² centralizado — Text 3D nativo (recebe Bloom + nao quebra
          em transformacoes/orbita, ao contrario do Html). */}
      <Text
        position={[0, 0.05, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.25}
        color={COLOR_STAKE}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.008}
        outlineColor="#000000"
        outlineOpacity={0.6}
      >
        M²
      </Text>
    </group>
  );
}

export default Terreno;
