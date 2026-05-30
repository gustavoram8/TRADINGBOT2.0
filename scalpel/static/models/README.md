# Synapse hologram — 3D model files

The Synapse view (Premium) renders a floating **brain** above a wireframe **head**.
Both meshes are loaded by `index.html` and auto-framed (centred + uniformly scaled),
so any reasonable OBJ/GLB drops in with the same on-screen size and the identical
holographic treatment (colour, opacity, wireframe).

## How the loader picks a file

`index.html` tries these sources in order and uses the first that loads:

| Mesh  | 1st choice  | 2nd choice  |
|-------|-------------|-------------|
| Brain | `brain.glb` | `brain.obj` |
| Head  | `head.glb`  | `head.obj`  |

`.glb` is preferred if present, so you can later swap in a `.glb` without code changes.

## Models currently in use

- **Brain → `brain.obj`** — converted from `final.stl`
  (FreeSurfer MRI Brain by *dgallichan*), license **CC BY 4.0**
  https://sketchfab.com/3d-models/brain-cadd2bde67404c43b2359a6a3281d84a

- **Head → `head.glb`** — Lee Perry-Smith head scan by **Infinite Realities**,
  distributed via the official Three.js examples, license **CC BY 3.0 Unported**
  https://github.com/mrdoob/three.js/tree/dev/examples/models/gltf/LeePerrySmith

## ⚠️ Attribution (required — both are CC BY)

The credit line is already in the site footer (`index.html`):

> Synapse 3D models: head scan by Lee Perry-Smith / Infinite Realities (CC BY 3.0) ·
> brain model by dgallichan (CC BY 4.0, Sketchfab)

## After you swap a model

Tell Claude. The face may need a one-line facing tweak (`HEAD_ROT` in `index.html`)
depending on which axis the head mesh ships with — Claude will tune it so the face
looks toward the camera.
