# FreeCAD CLI

Een command-line interface voor **FreeCAD** waarmee je parametrische 3D-modellen kunt maken, bewerken en exporteren zonder de GUI te openen. Inclusief volledige ondersteuning voor 2D bouwtekeningen (TechDraw).

## Kenmerken

- **3D Modellering** - Primitieven (box, cilinder, bol, kegel, torus), boolean-operaties, positionering
- **2D Sketches** - Lijnen, cirkels, bogen, rechthoeken met constraints
- **TechDraw Bouwtekeningen** - Aanzichten, projectiegroepen, doorsneden, uitvergrotingen, maatvoering, titelblok, hartlijnen, arceringen, verwijslijnen, ballonnen, stuklijst (BOM)
- **Export** - STEP, STL, OBJ, IGES, BREP, DXF, SVG, PDF
- **Interactieve REPL** en one-shot commando's
- **JSON output** voor AI-agent integratie
- **Undo/redo** met sessie-geschiedenis

## Vereisten

**FreeCAD** moet geinstalleerd zijn:

```bash
# Debian/Ubuntu
apt install freecad

# macOS
brew install --cask freecad

# Arch Linux
pacman -S freecad

# Windows
winget install FreeCAD
```

Controleer:
```bash
freecadcmd --version
```

## Installatie

```bash
git clone https://github.com/Pimmetjeoss/FreeCAD_CLI.git
cd FreeCAD_CLI
pip install -e .
```

## Snelstart

```bash
# Nieuw project
cli-anything-freecad project new -n Dressoir -o dressoir.json

# 3D objecten toevoegen
cli-anything-freecad --project dressoir.json part box -l 900 -w 500 -H 800 -n Kast
cli-anything-freecad --project dressoir.json part box -l 900 -w 500 -H 20 -n Bovenpaneel --pz 800

# Bouwtekening maken
cli-anything-freecad --project dressoir.json techdraw page -n Blad1 -t A3_Landscape -s 0.1
cli-anything-freecad --project dressoir.json techdraw view Blad1 Kast -d front-elevation
cli-anything-freecad --project dressoir.json techdraw view Blad1 Kast -d side-elevation -x 300
cli-anything-freecad --project dressoir.json techdraw dimension Blad1 View -t DistanceX
cli-anything-freecad --project dressoir.json techdraw title-block Blad1 \
  --title "Bouwtekening Dressoir" --material "Eiken massief" --scale "1:10"

# Stuklijst
cli-anything-freecad --project dressoir.json techdraw bom Blad1 \
  -i "item=1,name=Kast,material=Eiken,quantity=1" \
  -i "item=2,name=Bovenpaneel,material=Eiken,quantity=1"

# Exporteren
cli-anything-freecad --project dressoir.json techdraw export-svg Blad1 dressoir.svg --overwrite
cli-anything-freecad --project dressoir.json export step dressoir.step --overwrite
```

## Commando-overzicht

| Groep | Commando's |
|-------|-----------|
| `project` | `new`, `open`, `save`, `info`, `close` |
| `part` | `box`, `cylinder`, `sphere`, `cone`, `torus`, `fuse`, `cut`, `common`, `fillet`, `chamfer`, `move`, `list` |
| `sketch` | `new`, `line`, `circle`, `arc`, `rect`, `constrain`, `close`, `list` |
| `mesh` | `import`, `from-part` |
| `techdraw` | `page`, `view`, `projection`, `section`, `detail`, `dimension`, `annotate`, `title-block`, `centerline`, `hatch`, `leader`, `balloon`, `bom`, `list`, `export-dxf`, `export-svg`, `export-pdf` |
| `export` | `step`, `stl`, `obj`, `iges`, `brep`, `render`, `formats` |
| `session` | `status`, `undo`, `redo`, `history` |

## TechDraw 2D-tekeningen

Volledige ondersteuning voor professionele bouwtekeningen:

```bash
# Titelblok
techdraw title-block Blad1 --title "..." --author "..." --material "..." --scale "1:10"

# Uitvergroting (detail view)
techdraw detail Blad1 Box FrontView --ax 10 --ay 5 -r 15 -s 3.0

# Hartlijnen
techdraw centerline Blad1 FrontView -o vertical -p 50

# Arcering (doorsneden)
techdraw hatch Blad1 SectionView -f Face0 -p ansi31

# Verwijslijnen
techdraw leader Blad1 FrontView --sx 10 --sy 20 --ex 60 --ey 70 -t "Zie detail A"

# Ballonnen (itemnummering)
techdraw balloon Blad1 FrontView -t "1" -s circular -x 80 -y 30

# Stuklijst (BOM)
techdraw bom Blad1 -i "item=1,name=Zijpaneel,material=Eiken,quantity=2"
```

## JSON modus

Alle commando's ondersteunen `--json` output voor integratie met AI-agents:

```bash
cli-anything-freecad --json --project p.json part box -l 20
# {"name": "Box", "type": "Part::Box", "params": {"length": 20.0, ...}}
```

## Architectuur

```
cli_anything/freecad/
  freecad_cli.py          # Click CLI entry point + REPL
  core/
    project.py            # Project state (JSON) + FreeCAD script generation
    session.py            # Undo/redo met deep-copy snapshots
    techdraw.py           # 2D tekeningen, views, dimensies, export
    export.py             # Export pipeline (project -> FCStd -> STEP/STL/etc.)
  utils/
    freecad_backend.py    # freecadcmd subprocess wrapper
    repl_skin.py          # Interactieve REPL styling
  tests/
    test_core.py          # Unit + CLI tests (132 tests)
    test_full_e2e.py      # End-to-end tests met FreeCAD backend
```

De CLI slaat projectstatus op als JSON. Bij export/save genereert het een FreeCAD Python-script en voert het uit via `freecadcmd` (headless). Zo gebruikt alle geometrie de echte OpenCASCADE kernel.

## Tests

```bash
pip install -e .
pytest cli_anything/freecad/tests/ -v
```

## Licentie

MIT
