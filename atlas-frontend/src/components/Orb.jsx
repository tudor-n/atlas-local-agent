import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';

// The actual 3D mesh
function HologramSphere({ isSpeaking }) {
  const meshRef = useRef();

  useFrame((state) => {
    // Slowly rotate the orb
    meshRef.current.rotation.x = state.clock.elapsedTime * 0.2;
    meshRef.current.rotation.y = state.clock.elapsedTime * 0.3;

    // Pulse effect when speaking
    const scale = isSpeaking ? 1 + Math.sin(state.clock.elapsedTime * 10) * 0.05 : 1;
    meshRef.current.scale.set(scale, scale, scale);
  });

  return (
    <Sphere ref={meshRef} args={[1, 32, 32]}>
      <MeshDistortMaterial
        color="#00f3ff"
        attach="material"
        distort={isSpeaking ? 0.4 : 0.2} // More chaotic when talking
        speed={isSpeaking ? 5 : 2}
        wireframe={true}
        transparent={true}
        opacity={0.8}
      />
    </Sphere>
  );
}

// The Canvas wrapper
export default function Orb({ isSpeaking }) {
  return (
    <div className="w-full h-full drop-shadow-[0_0_15px_rgba(0,243,255,0.8)]">
      <Canvas camera={{ position: [0, 0, 3] }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        <HologramSphere isSpeaking={isSpeaking} />
      </Canvas>
    </div>
  );
}