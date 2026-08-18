import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, OrbitControls, Stars } from '@react-three/drei'
import * as THREE from 'three'
import { useScanStore } from '../store'
import { computeRiskScore, scoreColor, SEVERITY_STYLES } from '../lib/severity'
import type { Finding } from '../types'

function hashString(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h)
}

function particlePos(i: number, n: number): [number, number, number] {
  const golden = Math.PI * (3 - Math.sqrt(5))
  const y = 1 - (i / Math.max(1, n)) * 2
  const r = Math.sqrt(Math.max(0, 1 - y * y))
  const theta = golden * i
  return [Math.cos(theta) * r * 2.6, y * 2.6, Math.sin(theta) * r * 2.6]
}

const PARTICLE_SIZE: Record<Finding['severity'], number> = {
  Critical: 0.2,
  High: 0.16,
  Medium: 0.12,
  Low: 0.09,
}

function RiskOrb({ score, spinning }: { score: number; spinning: boolean }) {
  const inner = useRef<THREE.Mesh>(null)
  const wire = useRef<THREE.Mesh>(null)
  const color = scoreColor(score)

  useFrame((_, delta) => {
    const speed = spinning ? 0.02 : 0.005
    if (inner.current) inner.current.rotation.y += delta * speed
    if (wire.current) {
      wire.current.rotation.y -= delta * speed * 1.3
      wire.current.rotation.x += delta * speed * 0.6
    }
  })

  return (
    <Float speed={2} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={wire}>
        <icosahedronGeometry args={[1.45, 1]} />
        <meshStandardMaterial
          color={color}
          wireframe
          transparent
          opacity={0.22}
          emissive={color}
          emissiveIntensity={0.15}
        />
      </mesh>
      <mesh ref={inner}>
        <icosahedronGeometry args={[1.05, 1]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.55}
          roughness={0.25}
          metalness={0.45}
        />
      </mesh>
    </Float>
  )
}

function FindingParticles({ findings }: { findings: Finding[] }) {
  const items = useMemo(
    () =>
      findings.slice(0, 150).map((f, i) => ({
        key: `${f.source}-${f.type}-${f.line}`,
        pos: particlePos(i, Math.max(findings.length, 1)),
        color: SEVERITY_STYLES[f.severity].hex,
        size: PARTICLE_SIZE[f.severity],
        seed: hashString(f.type + f.line),
      })),
    [findings],
  )
  const group = useRef<THREE.Group>(null)
  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * 0.05
  })

  return (
    <group ref={group}>
      {items.map((it) => (
        <Float key={it.key} speed={1.5} rotationIntensity={0.35} floatIntensity={0.55}>
          <mesh position={it.pos}>
            <sphereGeometry args={[it.size, 16, 16]} />
            <meshStandardMaterial
              color={it.color}
              emissive={it.color}
              emissiveIntensity={0.65}
              roughness={0.3}
            />
          </mesh>
        </Float>
      ))}
    </group>
  )
}

export default function RiskScene3D() {
  const result = useScanStore((s) => s.result)
  const isScanning = useScanStore((s) => s.isScanning)
  const streamFindings = useScanStore((s) => s.streamFindings)

  const findings = result?.findings ?? streamFindings
  const risk = result?.risk_score ?? computeRiskScore(streamFindings)

  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: [0, 0.6, 8.2], fov: 50 }}
      gl={{ antialias: true }}
      className="!absolute inset-0"
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[5, 6, 5]} intensity={1.6} color="#c4b5fd" />
      <directionalLight position={[-6, -4, -3]} intensity={0.8} color="#818cf8" />
      <Stars radius={42} depth={32} count={1100} factor={3} saturation={0} fade speed={0.7} />
      <RiskOrb score={risk} spinning={isScanning} />
      <FindingParticles findings={findings} />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={isScanning ? 2.5 : 0.7}
      />
    </Canvas>
  )
}