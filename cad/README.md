# CAD design bank

3D-printable experimental components. All models were designed with Autodesk
Fusion 360 and printed on a Bambu Lab X1E.

**License: CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
You may share and adapt these models, including commercially, with attribution
to the paper (see repository README).

## Components

Every part is provided as a binary STL (millimetres, exported from Fusion 360),
ready to slice, and — where available — as the editable Fusion 360 source.
Bounding boxes are taken from the meshes.

| Directory | Component | Print file | Editable source | Size X × Y × Z (mm) |
|---|---|---|---|---|
| `robot-arm-holder/` | Pedestal that fixes the robot arm (Dobot Magician) to the bench and raises it by 210 mm | `dobot_magician_holder_210mm.stl` | `dobot_magician_holder_210mm.f3d` | 150 × 150 × 211 |
| `pipette-holder/` | Holder fixing the electric pipette (Sartorius Picus 2) to the robot arm tip | `picus2_holder.stl` | `picus2_holder.f3d` | 32 × 67 × 135 |
| `balance-cover/` | Liquid-splash cover for the electronic balance (Sartorius BCE822i), with windshield | `balance_cover_bce822i.stl` | *not yet added* | 275 × 240 × 109 |
| `imaging-stand/` | Holding stand for the appearance-imaging system (light, sample, camera) | `imaging_stand_assembly.stl` (one mesh of the whole assembly) | `imaging_stand_assembly.f3z` (Fusion archive: stand, assembly and light fixture designs) | 204 × 90 × 100 |
| `imaging-stand/` | Light shield placed over the imaging stand | `imaging_stand_light_shield.stl` | `imaging_stand_light_shield.f3d` | 250 × 120 × 120 |

Notes:

- `.f3d` is a single Fusion 360 design; `.f3z` is a Fusion 360 archive that bundles
  an assembly with the designs it references. Open either with *File → Open* in
  Fusion 360 (upload to your project).
- The meshes were checked to be closed (no open edges). `dobot_magician_holder_210mm.stl`
  is exported from a multi-body design, so a few internal faces are shared between
  touching bodies; slicers merge these, but re-export from the `.f3d` if your tool
  complains about non-manifold edges.
- The original file names were Japanese; they were renamed to ASCII for portability.
  Same geometry.
- STEP exports are not included; export them from the `.f3d` / `.f3z` sources if you
  need a neutral format.

<!-- TODO: add balance-cover .f3d.
     Add recommended print settings (material, layer height, infill) per component. -->
