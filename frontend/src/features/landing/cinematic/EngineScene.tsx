import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment as EnvMap, Lightformer } from "@react-three/drei";
import { Bloom, EffectComposer, Noise, Vignette } from "@react-three/postprocessing";
import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { createMaterials, PALETTE, type SceneMaterials } from "./materials";
import { architecture, bevelPlateGeometry, ringDetails, ringSegments, spokes } from "./engineParts";

type Props = { mobile: boolean; animate: boolean; active: boolean; onContextLost: () => void };

function Instanced({
  matrices,
  geometry,
  material,
}: {
  matrices: THREE.Matrix4[];
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}) {
  const ref = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    matrices.forEach((mx, i) => mesh.setMatrixAt(i, mx));
    mesh.instanceMatrix.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [matrices]);
  return (
    <instancedMesh ref={ref} args={[geometry, material, matrices.length]} frustumCulled={false} />
  );
}

type RingSpec = {
  r: number;
  n: number;
  w: number;
  d: number;
  mat: "ceramic" | "titanium" | "silver";
  tilt: [number, number];
  speed: number;
};

const RINGS: RingSpec[] = [
  { r: 1.5, n: 16, w: 0.26, d: 0.7, mat: "titanium", tilt: [0, 0], speed: 0.12 },
  { r: 2.15, n: 24, w: 0.34, d: 0.55, mat: "ceramic", tilt: [0.1, 0.05], speed: -0.07 },
  { r: 2.95, n: 12, w: 0.55, d: 0.8, mat: "ceramic", tilt: [0.2, -0.08], speed: 0.045 },
  { r: 3.75, n: 36, w: 0.18, d: 0.35, mat: "silver", tilt: [-0.12, 0.2], speed: -0.03 },
  { r: 4.55, n: 8, w: 0.7, d: 0.6, mat: "ceramic", tilt: [0.28, 0.1], speed: 0.02 },
];

function Engine({
  mats,
  mobile,
  animate,
}: {
  mats: SceneMaterials;
  mobile: boolean;
  animate: boolean;
}) {
  const box = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  const plate = useMemo(() => bevelPlateGeometry(), []);
  const bolt = useMemo(() => new THREE.CylinderGeometry(1, 1, 1, 6), []);
  const detail = mobile ? 0.5 : 1;
  const data = useMemo(
    () =>
      RINGS.map((rs) => {
        const fill = rs.n < 15 ? 0.8 : 0.9;
        return {
          plates: ringSegments(rs.r, rs.n, [1, rs.w, rs.d], fill),
          flangeF: ringSegments(
            rs.r - rs.w * 0.1,
            rs.n,
            [1, rs.w * 1.25, 0.05],
            fill * 0.92,
            0,
            rs.d / 2 + 0.06,
          ),
          flangeB: ringSegments(
            rs.r - rs.w * 0.1,
            rs.n,
            [1, rs.w * 1.25, 0.05],
            fill * 0.92,
            0,
            -rs.d / 2 - 0.06,
          ),
          cavity: ringSegments(rs.r - rs.w * 0.62, rs.n, [1, 0.08, rs.d * 0.8], 0.97),
          conduit: ringSegments(rs.r + rs.w * 0.56, rs.n * 2, [1, 0.03, 0.03], 0.6),
          ...ringDetails(rs.r, rs.n, rs.w, rs.d + 0.12, detail),
        };
      }),
    [detail],
  );
  const spokeA = useMemo(() => spokes(0.78, 1.35, 24, 0.07), []);
  const spokeB = useMemo(() => spokes(1.68, 1.98, 36, 0.05, 0.05), []);
  const groups = useRef<(THREE.Group | null)[]>([]);
  const core = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (!animate) return;
    const dt = Math.min(delta, 0.05);
    groups.current.forEach((g, i) => {
      if (g) g.rotation.z += RINGS[i]!.speed * dt;
    });
    if (core.current) {
      (core.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
        3 + Math.sin(state.clock.elapsedTime * 0.8) * 0.8;
    }
  });

  return (
    <group>
      <mesh ref={core}>
        <icosahedronGeometry args={[0.5, 4]} />
        <meshStandardMaterial
          color={PALETTE.blue}
          emissive="#4F8DF7"
          emissiveIntensity={3}
          toneMapped={false}
        />
      </mesh>
      <mesh material={mats.glass}>
        <sphereGeometry args={[0.8, 48, 32]} />
      </mesh>
      <mesh material={mats.cavity}>
        <torusGeometry args={[0.98, 0.14, 16, 72]} />
      </mesh>
      <mesh material={mats.silver}>
        <torusGeometry args={[1.12, 0.035, 8, 96]} />
      </mesh>
      <Instanced matrices={spokeA} geometry={box} material={mats.silver} />
      <Instanced matrices={spokeB} geometry={box} material={mats.cobalt} />
      {RINGS.map((rs, i) => {
        const d = data[i]!;
        return (
          <group key={i} rotation={[rs.tilt[0], rs.tilt[1], 0]}>
            <group
              ref={(g) => {
                groups.current[i] = g;
              }}
            >
              <Instanced matrices={d.plates} geometry={plate} material={mats[rs.mat]} />
              <Instanced matrices={d.flangeF} geometry={box} material={mats.titanium} />
              <Instanced matrices={d.flangeB} geometry={box} material={mats.titanium} />
              <Instanced matrices={d.cavity} geometry={box} material={mats.cavity} />
              <Instanced matrices={d.clamps} geometry={box} material={mats.cobalt} />
              <Instanced matrices={d.bolts} geometry={bolt} material={mats.silver} />
              <Instanced matrices={d.vents} geometry={box} material={mats.cavity} />
              <Instanced matrices={d.conduit} geometry={box} material={mats.energy} />
            </group>
          </group>
        );
      })}
      <mesh material={mats.titanium}>
        <cylinderGeometry args={[0.13, 0.13, 13, 16]} />
      </mesh>
      {[-1, 1].map((sgn) => (
        <group key={sgn} position={[0, sgn * 5.5, 0]}>
          <mesh material={mats.ceramic}>
            <cylinderGeometry args={[0.55, 0.85, 0.55, 32]} />
          </mesh>
          <mesh material={mats.cavity} position={[0, sgn * 0.35, 0]}>
            <cylinderGeometry args={[0.4, 0.4, 0.2, 24]} />
          </mesh>
          <mesh
            material={mats.energy}
            position={[0, sgn * -0.32, 0]}
            rotation={[Math.PI / 2, 0, 0]}
          >
            <torusGeometry args={[0.7, 0.02, 8, 48]} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function Modules({
  mats,
  mobile,
  animate,
}: {
  mats: SceneMaterials;
  mobile: boolean;
  animate: boolean;
}) {
  const count = mobile ? 6 : 11;
  const specs = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const a = (i / count) * Math.PI * 2 + 0.4;
        const r = 6.2 + (i % 3) * 1.2;
        return {
          pos: new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r * 0.62, -1.5 + (i % 4) * 1.1),
          phase: i * 1.7,
          scale: 0.7 + (i % 3) * 0.2,
        };
      }),
    [count],
  );
  const energy = useMemo(() => specs.map(() => mats.energy.clone()), [specs, mats]);
  const refs = useRef<(THREE.Group | null)[]>([]);
  useFrame((state) => {
    if (!animate) return;
    const t = state.clock.elapsedTime;
    specs.forEach((sp, i) => {
      const g = refs.current[i];
      if (g) {
        g.position.y = sp.pos.y + Math.sin(t * 0.3 + sp.phase) * 0.15;
        g.rotation.y = t * 0.08 + sp.phase;
      }
      const pulse = Math.max(0, Math.sin(t * 0.6 + sp.phase * 2.3));
      energy[i]!.emissiveIntensity = 0.8 + Math.pow(pulse, 8) * 5;
    });
  });
  return (
    <>
      {specs.map((sp, i) => (
        <group
          key={i}
          ref={(g) => {
            refs.current[i] = g;
          }}
          position={sp.pos}
          scale={sp.scale}
          rotation={[0.2, sp.phase, 0.1]}
        >
          <mesh material={mats.ceramic}>
            <cylinderGeometry args={[0.28, 0.28, 1.1, 12]} />
          </mesh>
          <mesh material={mats.titanium} position={[0, 0.65, 0]}>
            <cylinderGeometry args={[0.18, 0.3, 0.22, 12]} />
          </mesh>
          <mesh material={mats.titanium} position={[0, -0.65, 0]}>
            <cylinderGeometry args={[0.3, 0.18, 0.22, 12]} />
          </mesh>
          <mesh material={mats.cavity}>
            <boxGeometry args={[0.62, 0.7, 0.14]} />
          </mesh>
          <mesh material={energy[i]!} position={[0, 0, 0.08]}>
            <boxGeometry args={[0.05, 0.6, 0.02]} />
          </mesh>
        </group>
      ))}
    </>
  );
}

function makeShaftTexture() {
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 256;
  const g = c.getContext("2d")!;
  const grad = g.createLinearGradient(0, 0, 64, 0);
  grad.addColorStop(0, "rgba(255,255,255,0)");
  grad.addColorStop(0.5, "rgba(255,255,255,0.9)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 256);
  const v = g.createLinearGradient(0, 0, 0, 256);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(0.4, "rgba(0,0,0,1)");
  v.addColorStop(1, "rgba(0,0,0,0)");
  g.globalCompositeOperation = "destination-in";
  g.fillStyle = v;
  g.fillRect(0, 0, 64, 256);
  return new THREE.CanvasTexture(c);
}

function Architecture({ mats, mobile }: { mats: SceneMaterials; mobile: boolean }) {
  const box = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  const arch = useMemo(() => architecture(mobile ? 8 : 14), [mobile]);
  const shaft = useMemo(() => makeShaftTexture(), []);
  return (
    <>
      <Instanced matrices={arch.cols} geometry={box} material={mats.haze} />
      <Instanced matrices={arch.bridges} geometry={box} material={mats.haze} />
      <mesh material={mats.haze} position={[-4, 6, -50]} rotation={[0.15, 0.4, 0]}>
        <torusGeometry args={[26, 1, 8, 128]} />
      </mesh>
      {/* faint distant platform */}
      <mesh material={mats.haze} position={[4, -16, -18]}>
        <cylinderGeometry args={[14, 15, 1.2, 64]} />
      </mesh>
      {/* soft light shafts behind engine */}
      {[-3, 2.5, 8].map((x, i) => (
        <mesh key={i} position={[x + 4, 4, -14]} rotation={[0, 0, -0.35]}>
          <planeGeometry args={[3.5 + i, 40]} />
          <meshBasicMaterial
            map={shaft}
            transparent
            opacity={0.35}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            fog={false}
          />
        </mesh>
      ))}
    </>
  );
}

function Foreground({ mats, animate }: { mats: SceneMaterials; animate: boolean }) {
  const plate = useMemo(() => bevelPlateGeometry(), []);
  const box = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  const bolt = useMemo(() => new THREE.CylinderGeometry(1, 1, 1, 6), []);
  const parts = useMemo(() => {
    const plates = ringSegments(6, 20, [1, 1.1, 0.9], 0.92).slice(0, 6);
    const det = ringDetails(6, 20, 1.1, 1.02, 1);
    return {
      plates,
      flange: ringSegments(5.3, 20, [1, 0.12, 1.1], 0.95).slice(0, 6),
      energy: ringSegments(6.62, 40, [1, 0.04, 0.04], 0.7).slice(0, 12),
      bolts: det.bolts.slice(0, (det.bolts.length * 6) / 20),
      clamps: det.clamps.slice(0, 6),
    };
  }, []);
  const ref = useRef<THREE.Group>(null);
  useFrame((_, d) => {
    if (animate && ref.current) ref.current.rotation.z += Math.min(d, 0.05) * 0.012;
  });
  return (
    <group position={[7.8, -6.2, 5]} rotation={[0.25, -0.5, 0.2]}>
      <group ref={ref}>
        <Instanced matrices={parts.plates} geometry={plate} material={mats.ceramic} />
        <Instanced matrices={parts.flange} geometry={box} material={mats.cavity} />
        <Instanced matrices={parts.clamps} geometry={box} material={mats.cobalt} />
        <Instanced matrices={parts.bolts} geometry={bolt} material={mats.silver} />
        <Instanced matrices={parts.energy} geometry={box} material={mats.energy} />
      </group>
    </group>
  );
}

function CameraRig({ mobile, animate }: { mobile: boolean; animate: boolean }) {
  const { camera, pointer } = useThree();
  const start = mobile ? 24 : 17;
  const t = useRef(0);
  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05);
    if (animate) t.current += dt;
    const push = Math.min(t.current / 40, 1);
    const tx = animate && !mobile ? pointer.x * 0.6 : 0;
    const ty = animate && !mobile ? pointer.y * 0.35 : 0;
    camera.position.x += (tx - camera.position.x) * (1 - Math.exp(-2 * dt));
    camera.position.y += (ty + 0.6 - camera.position.y) * (1 - Math.exp(-2 * dt));
    camera.position.z = start - push * 2;
    camera.lookAt(0, mobile ? 2 : 0, 0);
  });
  return null;
}

function Scene({ mobile, animate }: { mobile: boolean; animate: boolean }) {
  const mats = useMemo(() => createMaterials(), []);
  const post = !mobile;
  return (
    <>
      <color attach="background" args={[PALETTE.ice]} />
      <fog attach="fog" args={["#EAF3FF", 16, 70]} />
      <EnvMap resolution={128} frames={1}>
        <Lightformer intensity={3} position={[0, 8, 4]} scale={[14, 6, 1]} />
        <Lightformer
          intensity={1.6}
          color="#BFD6FF"
          position={[-8, 1, 2]}
          rotation-y={Math.PI / 2}
          scale={[20, 2, 1]}
        />
        <Lightformer
          intensity={1.2}
          color={PALETTE.blue}
          position={[8, -2, -3]}
          rotation-y={-Math.PI / 2}
          scale={[12, 1, 1]}
        />
        <Lightformer
          intensity={0.8}
          position={[0, -6, 0]}
          rotation-x={Math.PI / 2}
          scale={[20, 20, 1]}
        />
      </EnvMap>
      <hemisphereLight args={["#FFFFFF", "#8FA6C2", 0.7]} />
      <directionalLight position={[6, 10, 9]} intensity={2.2} />
      <directionalLight position={[-9, -3, -7]} intensity={3} color={PALETTE.blue} />
      <pointLight position={[0, 0, 1.5]} intensity={18} distance={8} color="#3B82F6" />
      <CameraRig mobile={mobile} animate={animate} />
      <group
        position={mobile ? [0, 8.2, -2] : [4.9, 0.3, 0]}
        rotation={[0.18, -0.85, 0.05]}
        scale={mobile ? 0.45 : 0.8}
      >
        <Engine mats={mats} mobile={mobile} animate={animate} />
        <Modules mats={mats} mobile={mobile} animate={animate} />
      </group>
      <Architecture mats={mats} mobile={mobile} />
      {!mobile && <Foreground mats={mats} animate={animate} />}
      {post && (
        <EffectComposer multisampling={0}>
          <Bloom intensity={0.7} luminanceThreshold={1} luminanceSmoothing={0.2} mipmapBlur />
          <Vignette offset={0.3} darkness={0.35} />
          <Noise opacity={0.035} />
        </EffectComposer>
      )}
    </>
  );
}

function FirstFrame({ onReady }: { onReady?: (() => void) | undefined }) {
  const done = useRef(false);
  useFrame(() => {
    if (done.current) return;
    done.current = true;
    requestAnimationFrame(() => onReady?.());
  });
  return null;
}

export default function EngineScene({
  mobile,
  animate,
  active,
  onContextLost,
  onFirstFrame,
}: Props & { onFirstFrame?: () => void }) {
  return (
    <Canvas
      aria-hidden
      frameloop={active ? (animate ? "always" : "demand") : "never"}
      dpr={[1, mobile ? 1.25 : 1.75]}
      camera={{ position: [0, 0.6, mobile ? 24 : 17], fov: 38, near: 0.1, far: 200 }}
      gl={{ antialias: !mobile, powerPreference: "high-performance" }}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 0.95;
        gl.domElement.addEventListener("webglcontextlost", (e) => {
          e.preventDefault();
          onContextLost();
        });
      }}
    >
      <Scene mobile={mobile} animate={animate} />
      <FirstFrame onReady={onFirstFrame} />
    </Canvas>
  );
}
