# CAD design bank

3D-printable experimental components. All models were designed with Autodesk
Fusion 360 and printed on a Bambu Lab X1E.

**License: CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
You may share and adapt these models, including commercially, with attribution
to the paper (see repository README).

## Components

All four parts are provided as binary STL (millimetres, exported from Fusion 360),
ready to slice. Bounding boxes are taken from the meshes.

| Directory | File | Component | Size X × Y × Z (mm) |
|---|---|---|---|
| `robot-arm-holder/` | `dobot_magician_holder_210mm.stl` | Pedestal that fixes the robot arm (Dobot Magician) to the bench and raises it by 210 mm | 150 × 150 × 211 |
| `pipette-holder/` | `picus2_holder.stl` | Holder fixing the electric pipette (Sartorius Picus 2) to the robot arm tip | 32 × 67 × 135 |
| `balance-cover/` | `balance_cover_bce822i.stl` | Liquid-splash cover for the electronic balance (Sartorius BCE822i), with windshield | 275 × 240 × 109 |
| `imaging-stand/` | `imaging_stand_assembly.stl` | Holding stand for the appearance-imaging system (light, sample, camera); exported as one mesh of the assembly | 204 × 90 × 100 |

Notes:

- The meshes were checked to be closed (no open edges). `dobot_magician_holder_210mm.stl`
  is exported from a multi-body design, so a few internal faces are shared between
  touching bodies; slicers merge these, but re-export from the source if your tool
  complains about non-manifold edges.
- The original file names were Japanese; they were renamed to ASCII for portability.
  Same geometry.

## Formats

| Format | Purpose | Status |
|---|---|---|
| `.stl` | Ready to slice and print | included |
| `.f3d` | Editable Fusion 360 source — modify dimensions for your own setup | not yet added |
| `.step` | Neutral exchange format for other CAD software | not yet added |

The editable sources live in Fusion 360 cloud; `.f3d` and `.step` exports will be
added to the same directories.

<!-- TODO: export F3D/STEP from Fusion 360 and place them next to the STL files.
     Add recommended print settings (material, layer height, infill) per component. -->
