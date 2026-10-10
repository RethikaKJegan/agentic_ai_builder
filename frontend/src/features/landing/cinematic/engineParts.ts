import * as THREE from "three";

/** Pure procedural layout helpers. Each returns transform matrices for instanced meshes. */
const q = new THREE.Quaternion();
const s = new THREE.Vector3();
const p = new THREE.Vector3();
const e = new THREE.Euler();

function mat(
  pos: [number, number, number],
  rot: [number, number, number],
  scale: [number, number, number],
) {
  p.set(...pos);
  q.setFromEuler(e.set(...rot));
  s.set(...scale);
  return new THREE.Matrix4().compose(p, q, s);
}

function seeded(seed: number) {
  let x = seed;
  return () => (x = (x * 9301 + 49297) % 233280) / 233280;
}

/** Unit bevelled plate (1x1x1, centred) so instanced ring plates catch highlights on their edges. */
export function bevelPlateGeometry() {
  const shape = new THREE.Shape();
  const h = 0.5 - 0.08;
  shape.moveTo(-h, -h);
  shape.lineTo(h, -h);
  shape.lineTo(h, h);
  shape.lineTo(-h, h);
  shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: 1 - 0.16,
    bevelEnabled: true,
    bevelThickness: 0.08,
    bevelSize: 0.08,
    bevelSegments: 2,
    curveSegments: 1,
  });
  g.translate(0, 0, -(1 - 0.16) / 2);
  g.computeVertexNormals();
  return g;
}

/** Segmented ring: `count` plates around radius r, leaving a gap between each. */
export function ringSegments(
  r: number,
  count: number,
  size: [number, number, number],
  fill = 0.86,
  phase = 0,
  z = 0,
) {
  const out: THREE.Matrix4[] = [];
  const arc = ((Math.PI * 2 * r) / count) * fill;
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + phase;
    out.push(
      mat(
        [Math.cos(a) * r, Math.sin(a) * r, z],
        [0, 0, a + Math.PI / 2],
        [arc * size[0], size[1], size[2]],
      ),
    );
  }
  return out;
}

/**
 * Ordered sub-assemblies for a segmented ring: bolt rows on both faces, vent slats,
 * clamps bridging each gap, and a cable run along the outer edge.
 */
export function ringDetails(r: number, count: number, w: number, d: number, detail = 1) {
  const bolts: THREE.Matrix4[] = [];
  const vents: THREE.Matrix4[] = [];
  const clamps: THREE.Matrix4[] = [];
  const step = (Math.PI * 2) / count;
  const boltsPer = Math.max(2, Math.round(((2 * Math.PI * r) / count) * 3 * detail));
  for (let i = 0; i < count; i++) {
    const a0 = i * step;
    for (let b = 0; b < boltsPer; b++) {
      const a = a0 + step * (0.12 + (0.76 * b) / Math.max(1, boltsPer - 1)) - step / 2;
      for (const side of [-1, 1]) {
        const rr = r + side * w * 0.32;
        bolts.push(
          mat(
            [Math.cos(a) * rr, Math.sin(a) * rr, d / 2 + 0.01],
            [Math.PI / 2, 0, 0],
            [0.035, 0.03, 0.035],
          ),
        );
      }
    }
    if (i % 2 === 0) {
      for (let v = 0; v < 4; v++) {
        const a = a0 - step * 0.15 + v * step * 0.1;
        vents.push(
          mat(
            [Math.cos(a) * r, Math.sin(a) * r, d / 2 + 0.005],
            [0, 0, a],
            [w * 0.42, 0.018, 0.02],
          ),
        );
      }
    }
    const ag = a0 + step / 2;
    clamps.push(
      mat([Math.cos(ag) * r, Math.sin(ag) * r, 0], [0, 0, ag], [w * 1.15, 0.09, d * 1.12]),
    );
  }
  return { bolts, vents, clamps };
}

/** Radial spokes between inner and outer radius. */
export function spokes(inner: number, outer: number, count: number, thickness: number, phase = 0) {
  const out: THREE.Matrix4[] = [];
  const len = outer - inner;
  const mid = inner + len / 2;
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + phase;
    out.push(
      mat([Math.cos(a) * mid, Math.sin(a) * mid, 0], [0, 0, a], [len, thickness, thickness]),
    );
  }
  return out;
}

/** Colossal architecture: two ranks of pillars plus horizontal bridges, fading into haze. */
export function architecture(rows: number, seed = 7) {
  const rnd = seeded(seed);
  const cols: THREE.Matrix4[] = [];
  const bridges: THREE.Matrix4[] = [];
  const ranks = [
    { d: 34, n: rows, w: 2.4 },
    { d: 60, n: Math.round(rows * 1.3), w: 4.5 },
  ];
  for (const rk of ranks) {
    const xs: number[] = [];
    for (let i = 0; i < rk.n; i++) {
      const x = -rk.d * 1.3 + (i / (rk.n - 1)) * rk.d * 2.6 + (rnd() - 0.5) * 3;
      xs.push(x);
      const w = rk.w * (0.7 + rnd() * 0.6);
      cols.push(mat([x, 0, -rk.d], [0, 0, 0], [w, 90, w * 0.8]));
    }
    for (let i = 0; i < xs.length - 1; i += 2) {
      const mid = (xs[i]! + xs[i + 1]!) / 2;
      const len = Math.abs(xs[i + 1]! - xs[i]!);
      const y = -4 + rnd() * 14;
      bridges.push(mat([mid, y, -rk.d], [0, 0, 0], [len, rk.w * 0.25, rk.w * 0.5]));
    }
  }
  return { cols, bridges };
}
