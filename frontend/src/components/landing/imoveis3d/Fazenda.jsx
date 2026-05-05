// @component Fazenda — icone 3D low-poly de propriedade rural grande.
// Casa-sede + 8 postes de cerca conectados + area verde grande + tanque/cocho.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_GROUND = '#3d6a4d';    // verde grama
const COLOR_HOUSE = '#f5f5f0';     // branco perolado
const COLOR_ROOF = '#8b4513';      // marrom (telhado rustico)
const COLOR_FENCE = '#c9a84c';     // dourado (cerca)
const COLOR_TANK = '#888';         // cinza metalico (cocho/tanque)
const COLOR_WATER = '#00d4ff';     // ciano (agua no tanque)

export function Fazenda({ scale = 1, ...props }) {
  const groundGeo = useMemo(() => new THREE.BoxGeometry(1.7, 0.06, 1.7), []);
  const houseBodyGeo = useMemo(() => new THREE.BoxGeometry(0.7, 0.5, 0.55), []);
  const houseRoofGeo = useMemo(() => new THREE.ConeGeometry(0.55, 0.32, 4), []);
  const fencePostGeo = useMemo(() => new THREE.CylinderGeometry(0.025, 0.025, 0.32, 8), []);
  const tankBodyGeo = useMemo(() => new THREE.CylinderGeometry(0.18, 0.18, 0.2, 16), []);
  const waterGeo = useMemo(() => new THREE.CircleGeometry(0.16, 16), []);

  // 8 postes em volta do perimetro
  const fencePosts = useMemo(() => {
    const half = 0.78;
    return [
      [-half, -0.42, -half],
      [   0, -0.42, -half],
      [ half, -0.42, -half],
      [ half, -0.42,    0],
      [ half, -0.42,  half],
      [   0, -0.42,  half],
      [-half, -0.42,  half],
      [-half, -0.42,    0],
    ];
  }, []);

  // Linhas horizontais conectando os postes (cerca)
  const fenceLinesGeo = useMemo(() => {
    const half = 0.78;
    const yMid = -0.32;
    const pts = [
      // Lado norte
      [-half, yMid, -half], [half, yMid, -half],
      // Lado leste
      [half, yMid, -half], [half, yMid, half],
      // Lado sul
      [half, yMid, half], [-half, yMid, half],
      // Lado oeste
      [-half, yMid, half], [-half, yMid, -half],
    ];
    const positions = new Float32Array(pts.flat());
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  return (
    <group {...props} scale={scale}>
      {/* Area verde grande (terreno da fazenda) */}
      <mesh geometry={groundGeo} position={[0, -0.55, 0]} receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_GROUND} metalness={0.1} roughness={0.85} />
      </mesh>

      {/* Casa-sede (centro-esquerda) */}
      <group position={[-0.3, -0.27, 0.15]}>
        <mesh geometry={houseBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_HOUSE} metalness={0.3} roughness={0.45} />
        </mesh>
        <mesh geometry={houseRoofGeo} position={[0, 0.41, 0]} rotation={[0, Math.PI / 4, 0]} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_ROOF} metalness={0.4} roughness={0.55} />
        </mesh>
      </group>

      {/* 8 postes de cerca dourados */}
      {fencePosts.map((p, i) => (
        <mesh key={`post-${i}`} geometry={fencePostGeo} position={p} castShadow frustumCulled>
          <meshStandardMaterial color={COLOR_FENCE} metalness={0.65} roughness={0.35} />
        </mesh>
      ))}

      {/* Linhas conectando postes (cerca horizontal) */}
      <lineSegments>
        <primitive object={fenceLinesGeo} attach="geometry" />
        <lineBasicMaterial color={COLOR_FENCE} transparent opacity={0.85} linewidth={1} />
      </lineSegments>

      {/* Cocho/tanque cilindrico (canto direito-frente) */}
      <group position={[0.45, -0.42, 0.4]}>
        <mesh geometry={tankBodyGeo} castShadow receiveShadow frustumCulled>
          <meshStandardMaterial color={COLOR_TANK} metalness={0.85} roughness={0.3} />
        </mesh>
        {/* Agua no cocho */}
        <mesh geometry={waterGeo} position={[0, 0.105, 0]} rotation={[-Math.PI / 2, 0, 0]} frustumCulled>
          <meshStandardMaterial color={COLOR_WATER} emissive={COLOR_WATER} emissiveIntensity={0.4} metalness={0.2} roughness={0.1} transparent opacity={0.85} />
        </mesh>
      </group>
    </group>
  );
}

export default Fazenda;
