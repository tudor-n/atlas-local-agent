import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';
import { motion } from 'framer-motion';

function HologramSphere({ isSpeaking }) {
  const meshRef = useRef();

  useFrame((state) => {
    meshRef.current.rotation.x = state.clock.elapsedTime * 0.2;
    meshRef.current.rotation.y = state.clock.elapsedTime * 0.3;

    const scale = isSpeaking ? 1 + Math.sin(state.clock.elapsedTime * 10) * 0.05 : 1;
    meshRef.current.scale.set(scale, scale, scale);
  });

  return (
    <Sphere ref={meshRef} args={[1, 32, 32]}>
      <MeshDistortMaterial
        color="#00f3ff"
        attach="material"
        distort={isSpeaking ? 0.4 : 0.2} 
        speed={isSpeaking ? 5 : 2}
        wireframe={true}
        transparent={true}
        opacity={0.8}
      />
    </Sphere>
  );
}

export default function Orb({ isSpeaking }) {
  return (
    <motion.div 
      whileHover={{ scale: 1.08, filter: "drop-shadow(0 0 25px rgba(0,243,255,1))" }}
      whileTap={{ scale: 0.9, rotate: 15 }}
      transition={{ type: "spring", stiffness: 300, damping: 15 }}
      className="w-full h-full drop-shadow-[0_0_15px_rgba(0,243,255,0.6)] cursor-pointer"
    >
      <Canvas camera={{ position: [0, 0, 3] }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        <HologramSphere isSpeaking={isSpeaking} />
      </Canvas>
    </motion.div>
  );
}