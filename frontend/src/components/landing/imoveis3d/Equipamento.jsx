// @component Equipamento — icone 3D low-poly de equipamento/maquina industrial.
// Cilindro deitado (corpo) + base retangular + engrenagem decorativa (TorusGeometry)
// + tubulacao saliente. Representa bens moveis avaliados pra garantia/penhor.
import React, { useMemo } from 'react';
import * as THREE from 'three';

const COLOR_BODY = '#a0a0a0';      // cinza-aco metalico
const COLOR_DARK = '#5a5a5a';      // cinza escuro (detalhes)
const COLOR_BASE = '#0d4f3c';      // verde marca (base)
const COLOR_GEAR = '#c9a84c';      // dourado (engrenagem)
const COLOR_PIPE = '#00d4ff';      // ciano (tubulacao/luz)

export function Equipamento({ scale = 1, ...props }) {
  // Cilindro principal deitado (rotacionado em Z = 90deg)
  const cylinderGeo = useMemo(() => new THREE.CylinderGeometry(0.32, 0.32, 1.1, 24), []);
  const baseGeo = useMemo(() => new THREE.BoxGeometry(1.3, 0.2, 0.7), []);
  const pillarGeo = useMemo(() => new THREE.BoxGeometry(0.12, 0.32, 0.5), []);
  // Engrenagem (Torus com poucos segmentos = aspecto facetado)
  const gearGeo = useMemo(() => new THREE.TorusGeometry(0.18, 0.06, 8, 16), []);
  const gearHubGeo = useMemo(() => new THREE.CylinderGeometry(0.08, 0.08, 0.05, 12), []);
  const pipeGeo = useMemo(() => new THREE.CylinderGeometry(0.05, 0.05, 0.4, 12), []);
  const valveGeo = useMemo(() => new THREE.SphereGeometry(0.07, 12, 12), []);
  const ringGeo = useMemo(() => new THREE.TorusGeometry(0.32, 0.04, 8, 24), []);

  return (
    <group {...props} scale={scale}>
      {/* Base verde retangular */}
      <mesh geometry={baseGeo} position={[0, -0.42, 0]} castShadow receiveShadow frustumCulled>
        <meshStandardMaterial color={COLOR_BASE} metalness={0.5} roughness={0.4} />
      </mesh>

      {/* Pilares de suporte */}
      <mesh geometry={pillarGeo} position={[-0.5, -0.16, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_DARK} metalness={0.85} roughness={0.3} />
      </mesh>
      <mesh geometry={pillarGeo} position={[0.5, -0.16, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_DARK} metalness={0.85} roughness={0.3} />
      </mesh>

      {/* Corpo cilindrico deitado (eixo principal) */}
      <mesh
        geometry={cylinderGeo}
        position={[0, 0.1, 0]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
        receiveShadow
        frustumCulled
      >
        <meshStandardMaterial color={COLOR_BODY} metalness={0.95} roughness={0.15} />
      </mesh>

      {/* Aneis decorativos no cilindro (3 faixas) */}
      {[-0.4, 0, 0.4].map((x, i) => (
        <mesh
          key={`ring-${i}`}
          geometry={ringGeo}
          position={[x, 0.1, 0]}
          rotation={[0, 0, Math.PI / 2]}
          frustumCulled
        >
          <meshStandardMaterial color={COLOR_DARK} metalness={0.95} roughness={0.2} />
        </mesh>
      ))}

      {/* Engrenagem dourada na lateral direita */}
      <group position={[0.6, 0.1, 0]}>
        <mesh geometry={gearGeo} rotation={[0, Math.PI / 2, 0]} castShadow frustumCulled>
          <meshStandardMaterial
            color={COLOR_GEAR}
            metalness={0.85}
            roughness={0.2}
            emissive={COLOR_GEAR}
            emissiveIntensity={0.15}
          />
        </mesh>
        <mesh geometry={gearHubGeo} rotation={[0, 0, Math.PI / 2]} frustumCulled>
          <meshStandardMaterial color={COLOR_DARK} metalness={0.9} roughness={0.2} />
        </mesh>
      </group>

      {/* Tubulacao saliente em cima */}
      <mesh geometry={pipeGeo} position={[-0.25, 0.5, 0]} castShadow frustumCulled>
        <meshStandardMaterial color={COLOR_DARK} metalness={0.9} roughness={0.25} />
      </mesh>

      {/* Valvula ciana no topo da tubulacao (luz indicadora) */}
      <mesh geometry={valveGeo} position={[-0.25, 0.72, 0]} frustumCulled>
        <meshStandardMaterial
          color={COLOR_PIPE}
          emissive={COLOR_PIPE}
          emissiveIntensity={0.7}
          metalness={0.4}
          roughness={0.15}
        />
      </mesh>
    </group>
  );
}

export default Equipamento;
