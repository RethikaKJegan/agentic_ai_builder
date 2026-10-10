import * as THREE from "three";

/** Shared scene palette and materials — created once per scene, never per frame. */
export const PALETTE = {
  white: "#FFFFFF",
  ice: "#EAF3FF",
  blue: "#2563EB",
  cobalt: "#102D68",
  titanium: "#A9BBCF",
  graphite: "#1E293B",
};

export function createMaterials() {
  return {
    ceramic: new THREE.MeshPhysicalMaterial({
      color: "#F4F8FD",
      roughness: 0.38,
      metalness: 0.0,
      clearcoat: 0.6,
      clearcoatRoughness: 0.35,
    }),
    titanium: new THREE.MeshStandardMaterial({
      color: PALETTE.titanium,
      roughness: 0.3,
      metalness: 0.9,
    }),
    silver: new THREE.MeshStandardMaterial({ color: "#E6EDF5", roughness: 0.12, metalness: 1 }),
    cavity: new THREE.MeshStandardMaterial({
      color: PALETTE.graphite,
      roughness: 0.65,
      metalness: 0.5,
    }),
    cobalt: new THREE.MeshStandardMaterial({
      color: PALETTE.cobalt,
      roughness: 0.35,
      metalness: 0.7,
    }),
    glass: new THREE.MeshPhysicalMaterial({
      color: "#DCEBFF",
      roughness: 0.15,
      metalness: 0,
      transmission: 0.85,
      transparent: true,
      opacity: 0.5,
      thickness: 0.6,
      ior: 1.3,
    }),
    energy: new THREE.MeshStandardMaterial({
      color: PALETTE.blue,
      emissive: "#3B82F6",
      emissiveIntensity: 3,
      roughness: 0.3,
      toneMapped: false,
    }),
    haze: new THREE.MeshStandardMaterial({ color: "#DCE7F4", roughness: 0.85, metalness: 0.15 }),
  };
}
export type SceneMaterials = ReturnType<typeof createMaterials>;
