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

`.glb` is preferred if present, so you can later swap in a `.glb` without code
changes. The previous models (`asaro_head.obj`, the external FreeSurfer URL) were
removed to keep the repo free of any unclear-license assets.

## Models currently in use (both CC-BY)

Both were downloaded from Sketchfab and are in place:

- **Brain → `brain.obj`** — converted from the downloaded `final.stl`
  (FreeSurfer MRI brain by *dgallichan*), license **CC BY**.
  https://sketchfab.com/3d-models/brain-cadd2bde67404c43b2359a6a3281d84a
- **Head → `head.obj`** — "Human Head Base Mesh" by *ferrumiron6*, license **CC BY**.
  https://sketchfab.com/3d-models/human-head-base-mesh-e3fa4d8aed5f45869e3d7c616a8a0841

## ⚠️ Attribution (required — both are CC BY)

CC BY permits commercial use but **requires crediting the author**. The credit
line is already in the site footer (`index.html`):

> Synapse 3D models: “Human Head Base Mesh” by ferrumiron6 · brain model by
> dgallichan — licensed under CC BY 4.0 (Sketchfab)

Tip: Sketchfab's **COPY CREDITS** button gives the exact attribution string for
each model — paste those if you want the precise wording.

## After you add the files

Tell Claude. The face may need a one-line facing tweak (`HEAD_ROT` in `index.html`)
depending on which axis the head mesh ships with — Claude will tune it so the face
looks toward the camera, matching the current look.
