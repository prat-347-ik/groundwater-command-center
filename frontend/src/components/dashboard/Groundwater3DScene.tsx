'use client';

import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { 
  OrbitControls, 
  Box, 
  Cylinder, 
  Environment, 
  Sky, 
  Text,
  Float
} from '@react-three/drei';
import * as THREE from 'three';

// --- Assets: Low Poly Tree ---
const Tree = ({ position, scale = 1 }: { position: [number, number, number], scale?: number }) => {
  return (
    <group position={position} scale={scale}>
      {/* Trunk */}
      <mesh position={[0, 0.4, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.05, 0.1, 0.8, 8]} />
        <meshStandardMaterial color="#5d4037" />
      </mesh>
      {/* Leaves */}
      <mesh position={[0, 1.2, 0]} castShadow receiveShadow>
        <coneGeometry args={[0.4, 1.2, 8]} />
        <meshStandardMaterial color="#2e7d32" roughness={0.8} />
      </mesh>
      <mesh position={[0, 1.8, 0]} castShadow receiveShadow>
        <coneGeometry args={[0.3, 1.0, 8]} />
        <meshStandardMaterial color="#388e3c" roughness={0.8} />
      </mesh>
    </group>
  );
};

// --- Rain Particle System ---
const Rain = ({ intensity }: { intensity: number }) => {
  // Cap particles to keep performance high
  const count = Math.min(intensity * 150, 3000); 
  const mesh = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Initialize random starting positions
  const particles = useMemo(() => {
    return new Array(3000).fill(0).map(() => ({
      speed: 0.1 + Math.random() * 0.1,
      x: (Math.random() - 0.5) * 8,
      y: Math.random() * 10,
      z: (Math.random() - 0.5) * 8,
    }));
  }, []);

  useFrame(() => {
    if (!mesh.current) return;
    
    particles.forEach((p, i) => {
      if (i < count) {
        // Animate falling
        p.y -= p.speed;
        if (p.y < 0) p.y = 8; // Reset to sky

        dummy.position.set(p.x, p.y, p.z);
        // Stretch raindrop slightly based on speed for motion blur effect
        dummy.scale.set(1, 1 + p.speed * 2, 1); 
        dummy.updateMatrix();
        mesh.current!.setMatrixAt(i, dummy.matrix);
      } else {
        // Hide unused
        dummy.position.set(0, -50, 0);
        dummy.updateMatrix();
        mesh.current!.setMatrixAt(i, dummy.matrix);
      }
    });
    mesh.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, 3000]}>
      <boxGeometry args={[0.03, 0.2, 0.03]} />
      <meshBasicMaterial color="#aaccff" transparent opacity={0.6} />
    </instancedMesh>
  );
};

// --- Main Scene Component ---
interface SceneProps {
  waterLevel: number; // e.g., depth in meters (0 to 50)
  rainfall: number;   // e.g., mm (0 to 100)
}

export default function Groundwater3DScene({ waterLevel, rainfall }: SceneProps) {
  // Normalize water level: 
  // Real world: 0m (surface) to 30m (deep)
  // 3D World Y-axis: 2.5 (surface) to -2.5 (bottom)
  const MAX_DEPTH = 30;
  const SCENE_HEIGHT = 5;
  const surfaceY = 2.5;
  
  // Calculate the top surface of the water in 3D space
  const waterSurfaceY = surfaceY - (waterLevel / MAX_DEPTH) * SCENE_HEIGHT;
  
  // Ensure water doesn't go above ground or below bottom
  const clampedWaterY = Math.max(-2.5, Math.min(surfaceY - 0.1, waterSurfaceY));
  
  // Calculate the height/thickness of the water volume
  const waterThickness = Math.abs(clampedWaterY - (-2.5));
  const waterCenterY = -2.5 + (waterThickness / 2);

  return (
    <div className="h-[500px] w-full bg-slate-900 rounded-xl overflow-hidden shadow-2xl border border-slate-700 relative">
      <Canvas shadows camera={{ position: [6, 4, 6], fov: 40 }}>
        {/* --- Lighting & Atmosphere --- */}
        <Sky sunPosition={[10, 10, 10]} turbidity={0.5} rayleigh={0.5} />
        <ambientLight intensity={0.4} />
        <directionalLight 
          position={[5, 10, 5]} 
          intensity={1.5} 
          castShadow 
          shadow-mapSize={[1024, 1024]} 
        />
        {/* Environment adds realistic reflections to the water */}
        <Environment preset="city" /> 

        <OrbitControls 
            enablePan={false} 
            maxPolarAngle={Math.PI / 2 - 0.1} // Prevent going under ground
            autoRotate 
            autoRotateSpeed={0.3} 
        />

        {/* --- 1. Top Soil Layer (The Ground) --- */}
        <group position={[0, 2.6, 0]}>
            {/* Grass Surface */}
            <Box args={[4.2, 0.2, 4.2]} receiveShadow castShadow>
                <meshStandardMaterial color="#4caf50" roughness={1} />
            </Box>
            
            {/* Vegetation */}
            <Tree position={[-1.2, 0.1, -1]} scale={0.8} />
            <Tree position={[1.5, 0.1, 1.2]} scale={1.1} />
            <Tree position={[-1, 0.1, 1.5]} scale={0.6} />

            {/* Well Head */}
            <group position={[0, 0.5, 0]}>
                <Cylinder args={[0.15, 0.15, 0.8]} castShadow>
                    <meshStandardMaterial color="#555" metalness={0.6} roughness={0.2} />
                </Cylinder>
                <Box args={[0.5, 0.1, 0.5]} position={[0, 0.4, 0]}>
                    <meshStandardMaterial color="#333" />
                </Box>
            </group>
        </group>

        {/* --- 2. The Earth Cross-Section (Container) --- */}
        {/* Transparent glass box representing the underground volume */}
        <Box args={[4, 5, 4]} position={[0, 0, 0]}>
             <meshPhysicalMaterial 
                color="#ffffff" 
                transmission={0.2} // Slight glass effect
                opacity={0.1} 
                transparent 
                roughness={0} 
                side={THREE.BackSide} // Render inside
             />
        </Box>
        
        {/* Frame / Edges for visual structure */}
        <gridHelper args={[4, 1, 0x888888, 0x888888]} position={[0, 2.5, 0]} />
        <gridHelper args={[4, 1, 0x444444, 0x444444]} position={[0, -2.5, 0]} />

        {/* --- 3. The Well Pipe (Infrastructure) --- */}
        <Cylinder args={[0.05, 0.05, 5]} position={[0, 0, 0]}>
            <meshStandardMaterial color="#888" metalness={0.8} />
        </Cylinder>

        {/* --- 4. The Aquifer (Dynamic Water Volume) --- */}
        {/* We use MeshPhysicalMaterial for realistic water looking glass/liquid */}
        <Box args={[3.9, waterThickness, 3.9]} position={[0, waterCenterY, 0]}>
            <meshPhysicalMaterial 
                color="#00aaff"
                transmission={0.6}  // Allows light to pass through (glass-like)
                thickness={3}       // Refraction volume
                roughness={0.1}     // Shiny surface
                ior={1.33}          // Index of refraction for water
                transparent
                opacity={0.8}
            />
        </Box>

        {/* --- 5. Bedrock (Bottom Layer) --- */}
        <Box args={[4, 0.5, 4]} position={[0, -2.75, 0]} receiveShadow>
             <meshStandardMaterial color="#3e2723" roughness={0.9} />
        </Box>

        {/* --- 6. Effects --- */}
        {rainfall > 0 && <Rain intensity={rainfall} />}
        
        {/* --- Labels --- */}
        <Float speed={2} rotationIntensity={0.1} floatIntensity={0.5}>
           <Text 
             position={[2.2, clampedWaterY, 2.2]} 
             fontSize={0.3} 
             color="white" 
             anchorX="left"
             outlineWidth={0.02}
             outlineColor="#000000"
           >
             {`Water Level: ${waterLevel.toFixed(1)}m`}
           </Text>
        </Float>

      </Canvas>

      {/* --- HUD Overlay --- */}
      <div className="absolute top-4 left-4 pointer-events-none">
          <div className="bg-black/40 backdrop-blur-md p-3 rounded-lg border border-white/10 text-white">
             <h3 className="text-xs uppercase tracking-widest text-slate-300 mb-1">Live Simulation</h3>
             <div className="flex items-center gap-2">
                 <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                 <span className="font-mono text-sm">Aquifer Depth: {waterLevel.toFixed(1)}m</span>
             </div>
             {rainfall > 0 && (
                <div className="flex items-center gap-2 mt-1">
                   <div className="w-2 h-2 rounded-full bg-blue-200"></div>
                   <span className="font-mono text-sm">Precipitation: {rainfall.toFixed(1)}mm</span>
                </div>
             )}
          </div>
      </div>
    </div>
  );
}