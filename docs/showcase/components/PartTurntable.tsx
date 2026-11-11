// PartTurntable: a printed part (a .glb from media/models/) turning slowly on a paper-coloured floor under a key
// light and a soft fill. It draws the whole frame (3D cannot be boxed), so put type over it with DOM in front.
// 3D renders at about 0.9 s a frame on this machine: keep it short on screen (2 to 4 s).
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame } from "raea";
import { Model } from "raea/3d";
import { Camera3d } from "raea/camera";
import { AmbientLight, DirectionalLight } from "raea/light";
import { Cuboid, Mesh3d } from "raea/mesh";
import { StandardMaterial } from "raea/pbr";
import { Transform } from "raea/transform";
import { C } from "../theme";
import { has } from "./media";
import { Placeholder } from "./PhotoStage";

export type PartTurntableProps = {
  /** path under media/ (default "models/name-tag-mum.glb", the MUM name tag from the plugin's name_tag.scad) */
  file?: string;
  /** the part's longest side in metres after the glb (mm to m); the name tag is 0.07. Used to frame the camera. */
  span?: number;
  /** turn in radians per second (default 0.5) and the starting angle (default -0.5) */
  speed?: number;
  start?: number;
  /** where the part sits across the frame: -1 left third .. 0 centre .. 1 right third (default 0) */
  offset?: number;
  /** camera height: 0 = level, 1 = looking well down onto the part (default 0.55) */
  tilt?: number;
  /** floor and background colour (default paper) */
  ground?: string;
};

export function PartTurntable({ file = "models/name-tag-mum.glb", span = 0.07, speed = 0.5, start = -0.5, offset = 0, tilt = 0.55, ground = C.paper }: PartTurntableProps) {
  const f = useCurrentFrame();
  if (!has(file)) return <Placeholder text="3D part goes here" file={file} />;
  const angle = start + (speed * f) / 30;
  // the model is scaled so its longest side is about 1 m in the scene: lights and camera stay the same for any part
  const k = 1 / span;
  const dist = 1.55;
  const camY = 0.15 + tilt * 1.2;
  // aim below the part so it sits a little above the middle of the frame, leaving the bottom for a Caption
  const look: [number, number, number] = [-offset * 0.5, -0.14, 0];
  return (
    <AbsoluteFill style={{ background: ground }}>
      <Camera3d transform={Transform.fromXyz(look[0], camY, dist).lookingAt(look)} projection={{ Perspective: { fov: (32 * Math.PI) / 180 } }} />
      <AmbientLight brightness={180} />
      <DirectionalLight transform={Transform.fromXyz(-3, 2.2, 2).lookingAt([0, 0, 0])} illuminance={7000} shadow_maps_enabled />
      <DirectionalLight transform={Transform.fromXyz(3, 1.5, -1).lookingAt([0, 0, 0])} illuminance={1800} />
      <Mesh3d transform={Transform.fromXyz(0, -0.02, 0)}>
        <Cuboid half_size={[8, 0.02, 8]} />
        <StandardMaterial base_color={ground} perceptual_roughness={0.95} />
      </Mesh3d>
      <Model name="part" src={staticFile(file)} position={[0, 0, 0]} rotation={[0, angle, 0]} scale={k} />
    </AbsoluteFill>
  );
}

/** Frames of turntable the film can afford: keep 3D on screen short. */
export const TURNTABLE_MAX_FRAMES = 120;
