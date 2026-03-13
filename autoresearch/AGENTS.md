# autoresearch — FreeCAD CAD Reconstruction

Autonomous agent that iteratively improves a FreeCAD Python script to reconstruct a reference STEP model.

## Setup

1. **Read the in-scope files** for full context:
   - `freecad_build.py` — the file you modify. Pure FreeCAD Python geometry.
   - `measure.py` — fixed. Computes score between experiment.step and reference.step.
   - `reference.json` — fixed. Ground truth geometry (volume, bbox, surface area).
   - `reference.png` — fixed. Visual reference render.
2. **Verify reference.step and reference.json exist** in autoresearch/.
3. **Initialize results.tsv** with just the header row if empty.
4. **Confirm and go.**

## Experimentation

Each experiment builds a STEP file. Run:
```
freecadcmd freecad_build.py > run.log 2>&1
```
Then render:
```
python render_step.py experiment.step experiment.png
```
Then measure:
```
python measure.py
```

**What you CAN do:**
- Modify `freecad_build.py` — this is the only file you edit. Geometry, boolean ops, fillets, chamfers, everything.

**What you CANNOT do:**
- Modify `measure.py`, `inspect_step.py`, `render_step.py`, `reference.step`, `reference.json`, or `reference.png`.
- Install new packages.
- Modify the scoring metric.

**The goal: get the highest score** (0-1, higher is better).

## Metric

```
score = 0.4 * volume_sim + 0.3 * bbox_sim + 0.15 * surface_sim + 0.15 * render_sim
```

- volume_sim: `max(0, 1 - |exp_vol - ref_vol| / ref_vol)` — most important
- bbox_sim: `max(0, 1 - manhattan_dist(exp_bbox, ref_bbox) / ref_diagonal)` — overall shape
- surface_sim: `max(0, 1 - |exp_sa - ref_sa| / ref_sa)` — detail fidelity
- render_sim: SSIM between experiment.png and reference.png — visual match

## Reference Model Details

File: `113-120-516.step` (SolidWorks 2021, STEP AP214)
- Cylindrical mechanical part: ~Ø36 x 28mm tall
- Multiple step-diameters: R18.0 (flange), R13.5 (body), R12.5, R7.5, R5.47
- Small holes R0.76mm in circular pattern
- 45° chamfers, R0.1mm fillets
- 139 faces, 1 solid body named "Verrundung1"
- Body of revolution (axially symmetric) with boolean cuts for holes

**Geometry (from reference.json):**
Check reference.json for exact values of volume, surface_area, bounding_box.

## Strategy Phases

Follow these phases in order. Move to the next phase when diminishing returns on the current one.

### Phase 1: Bounding Box + Volume
- Match bounding box dimensions exactly
- Simple cylinder R13.5 x H28 as starting point
- Target: volume_sim > 0.7, bbox_sim > 0.8

### Phase 2: Main Features — Profile + Revolution
- Create 2D sketch profile of the cross-section
- Revolve around Z-axis (body of revolution)
- Step-diameters: R18.0 flange at base, R13.5 body, R12.5, R7.5, R5.47
- Target: volume_sim > 0.9, bbox_sim > 0.95

### Phase 3: Holes
- Circular pattern of small holes R0.76mm
- Boolean cut operations
- Determine hole positions from reference geometry
- Target: volume_sim > 0.95

### Phase 4: Chamfers + Fillets
- 45° chamfers on sharp transitions
- R0.1mm edge fillets
- Target: surface_sim > 0.9

### Phase 5: Fine-tuning
- Micro-adjustments for maximum score
- Compare face/edge counts with reference
- Target: score > 0.95

## FreeCAD Python Tips

**Basic primitives:**
```python
import Part
cyl = Part.makeCylinder(radius, height)
box = Part.makeBox(length, width, height)
```

**Boolean operations:**
```python
result = shape_a.fuse(shape_b)     # union
result = shape_a.cut(shape_b)      # subtract
result = shape_a.common(shape_b)   # intersect
```

**Body of revolution (optimal for cylindrical parts):**
```python
# Create 2D wire profile
points = [FreeCAD.Vector(x1,0,z1), FreeCAD.Vector(x2,0,z2), ...]
wire = Part.makePolygon(points + [points[0]])  # closed
face = Part.Face(wire)
solid = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)
```

**Fillets and chamfers:**
```python
shape = shape.makeFillet(radius, edges_list)
shape = shape.makeChamfer(size, edges_list)
```

**Placement and transforms:**
```python
shape.translate(FreeCAD.Vector(dx, dy, dz))
shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), angle_deg)
```

## Output format

measure.py prints:
```
---
score:         0.123456
volume_sim:    0.200000
bbox_sim:      0.300000
surface_sim:   0.150000
render_sim:    0.100000
---
ref_volume:    12345.67
exp_volume:    11234.56
```

## Logging results

Log to `results.tsv` (tab-separated):

```
commit	score	volume_sim	bbox_sim	surface_sim	render_sim	time	status	description
```

1. git commit hash (short, 7 chars)
2. score (e.g. 0.3456)
3. volume_sim
4. bbox_sim
5. surface_sim
6. render_sim
7. build+measure time in seconds
8. status: `keep`, `discard`, or `crash`
9. short description of what changed

Example:
```
commit	score	volume_sim	bbox_sim	surface_sim	render_sim	time	status	description
a1b2c3d	0.450	0.600	0.700	0.200	0.100	5.2	keep	baseline cylinder
b2c3d4e	0.720	0.850	0.920	0.500	0.300	4.8	keep	revolution profile with step diameters
c3d4e5f	0.680	0.800	0.900	0.450	0.250	5.1	discard	wrong flange height
```

## The experiment loop

LOOP FOREVER:

1. Look at the current state: `git log`, `results.tsv`
2. Read `reference.json` for exact target values
3. Choose a change strategy based on the current phase
4. Modify `freecad_build.py`
5. `git commit`
6. `freecadcmd freecad_build.py > run.log 2>&1`
7. If build crashes: `tail -n 50 run.log`, attempt fix, else discard
8. `python render_step.py experiment.step experiment.png`
9. `python measure.py` → extract scores
10. Record in results.tsv
11. If score improved → keep commit
12. If not improved → `git reset --hard HEAD~1`
13. Repeat

**NEVER STOP**: The loop runs until manually interrupted. If stuck, try more radical changes, combine near-misses, or revisit earlier phases.

## Architecture Notes

- `freecad_build.py` runs inside FreeCAD's Python (FreeCAD, Part modules available)
- `measure.py` and `render_step.py` run in system Python (PIL, scikit-image, numpy, trimesh)
- STEP comparison is EXACT (volume/bbox, not pixels) → more reliable than render-only
- ~5-10 sec per iteration (much faster than Blender render loop)
- Body of revolution + boolean cuts = optimal strategy for cylindrical parts
