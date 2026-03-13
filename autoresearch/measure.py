"""Measure similarity between experiment and reference.

Combines geometric metrics (volume, bbox, surface area) with visual similarity.

Usage:
    python measure.py
    python measure.py --experiment experiment.step --reference reference.step

Metric:
    score = 0.4 * volume_sim + 0.3 * bbox_sim + 0.15 * surface_sim + 0.15 * render_sim
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.transform import resize as sk_resize

SCRIPT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# FreeCAD integration
# ---------------------------------------------------------------------------

def find_freecadcmd() -> str:
    """Find the FreeCADCmd executable."""
    for name in ("freecadcmd", "FreeCADCmd", "FreeCADCmd.exe", "freecad-cmd"):
        path = shutil.which(name)
        if path:
            return path
    common_paths = [
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    raise RuntimeError("FreeCADCmd not found. Install FreeCAD 1.0+.")


def extract_geometry(step_path: Path) -> dict:
    """Run inspect_step.py via FreeCADCmd and return geometry dict."""
    freecadcmd = find_freecadcmd()
    inspect_script = SCRIPT_DIR / "inspect_step.py"

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, prefix="geom_"
    ) as tmp:
        output_json = tmp.name

    try:
        proc = subprocess.run(
            [freecadcmd, str(inspect_script), str(step_path), "--output", output_json],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            print(f"[WARN] inspect_step stderr:\n{proc.stderr}", file=sys.stderr)

        if not os.path.exists(output_json):
            return {"error": f"inspect_step.py produced no output. stderr: {proc.stderr}"}

        with open(output_json) as f:
            return json.load(f)
    finally:
        if os.path.exists(output_json):
            os.unlink(output_json)


# ---------------------------------------------------------------------------
# Geometric similarity metrics
# ---------------------------------------------------------------------------

def volume_similarity(ref: dict, exp: dict) -> float:
    """max(0, 1 - |exp_vol - ref_vol| / ref_vol)"""
    ref_vol = ref["volume"]
    exp_vol = exp["volume"]
    if ref_vol == 0:
        return 0.0
    return max(0.0, 1.0 - abs(exp_vol - ref_vol) / ref_vol)


def bbox_similarity(ref: dict, exp: dict) -> float:
    """max(0, 1 - manhattan_dist(exp_bbox, ref_bbox) / ref_diagonal)"""
    rb = ref["bounding_box"]
    eb = exp["bounding_box"]

    ref_vals = [rb["xmin"], rb["ymin"], rb["zmin"], rb["xmax"], rb["ymax"], rb["zmax"]]
    exp_vals = [eb["xmin"], eb["ymin"], eb["zmin"], eb["xmax"], eb["ymax"], eb["zmax"]]

    manhattan = sum(abs(r - e) for r, e in zip(ref_vals, exp_vals))
    diagonal = rb["diagonal"]

    if diagonal == 0:
        return 0.0
    return max(0.0, 1.0 - manhattan / diagonal)


def surface_similarity(ref: dict, exp: dict) -> float:
    """max(0, 1 - |exp_sa - ref_sa| / ref_sa)"""
    ref_sa = ref["surface_area"]
    exp_sa = exp["surface_area"]
    if ref_sa == 0:
        return 0.0
    return max(0.0, 1.0 - abs(exp_sa - ref_sa) / ref_sa)


# ---------------------------------------------------------------------------
# Visual similarity (SSIM) — reused from autorender/measure.py
# ---------------------------------------------------------------------------

def load_image(path: Path) -> np.ndarray:
    """Load image as RGB numpy array."""
    img = Image.open(path).convert("RGB")
    return np.array(img)


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert RGB to grayscale."""
    return np.dot(img[..., :3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)


def resize_to_match(img: np.ndarray, target_shape: tuple[int, ...]) -> np.ndarray:
    """Resize img to target_shape using anti-aliased resize."""
    return (sk_resize(img, target_shape[:2] + img.shape[2:],
                      anti_aliasing=True, preserve_range=True)
            .astype(np.uint8))


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """Compute SSIM between two images (converts to grayscale)."""
    gray_a = to_grayscale(img_a)
    gray_b = to_grayscale(img_b)
    if gray_a.shape != gray_b.shape:
        gray_b = resize_to_match(
            gray_b.reshape(*gray_b.shape, 1),
            gray_a.shape
        ).squeeze()
    return ssim(gray_a, gray_b)


def render_similarity(ref_png: Path, exp_png: Path) -> float:
    """Compute render SSIM between reference and experiment PNGs."""
    if not ref_png.exists() or not exp_png.exists():
        return 0.0
    img_ref = load_image(ref_png)
    img_exp = load_image(exp_png)
    return compute_ssim(img_ref, img_exp)


# ---------------------------------------------------------------------------
# Combined score
# ---------------------------------------------------------------------------

def measure(ref_step: Path, exp_step: Path) -> dict:
    """Compute all similarity metrics.

    score = 0.4 * volume_sim + 0.3 * bbox_sim + 0.15 * surface_sim + 0.15 * render_sim
    """
    # Load reference geometry (prefer cached reference.json)
    ref_json_path = SCRIPT_DIR / "reference.json"
    if ref_json_path.exists():
        with open(ref_json_path) as f:
            ref_geom = json.load(f)
    else:
        ref_geom = extract_geometry(ref_step)

    # Extract experiment geometry
    exp_geom = extract_geometry(exp_step)

    if "error" in ref_geom:
        print(f"[ERROR] Reference geometry: {ref_geom['error']}")
        sys.exit(1)
    if "error" in exp_geom:
        return {
            "score": 0.0,
            "volume_sim": 0.0,
            "bbox_sim": 0.0,
            "surface_sim": 0.0,
            "render_sim": 0.0,
            "error": exp_geom["error"],
        }

    vol_sim = volume_similarity(ref_geom, exp_geom)
    bb_sim = bbox_similarity(ref_geom, exp_geom)
    surf_sim = surface_similarity(ref_geom, exp_geom)

    # Render similarity (optional — needs reference.png)
    ref_png = SCRIPT_DIR / "reference.png"
    exp_png = SCRIPT_DIR / "experiment.png"

    # Try to render experiment if experiment.step exists but experiment.png doesn't
    if exp_step.exists() and not exp_png.exists():
        try:
            render_script = SCRIPT_DIR / "render_step.py"
            subprocess.run(
                [sys.executable, str(render_script), str(exp_step), str(exp_png)],
                capture_output=True,
                timeout=120,
            )
        except Exception:
            pass

    rend_sim = render_similarity(ref_png, exp_png)

    score = 0.4 * vol_sim + 0.3 * bb_sim + 0.15 * surf_sim + 0.15 * rend_sim

    return {
        "score": score,
        "volume_sim": vol_sim,
        "bbox_sim": bb_sim,
        "surface_sim": surf_sim,
        "render_sim": rend_sim,
        "ref_volume": ref_geom["volume"],
        "exp_volume": exp_geom["volume"],
        "ref_surface_area": ref_geom["surface_area"],
        "exp_surface_area": exp_geom["surface_area"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure CAD reconstruction similarity.")
    parser.add_argument("--experiment", type=Path,
                        default=SCRIPT_DIR / "experiment.step")
    parser.add_argument("--reference", type=Path,
                        default=SCRIPT_DIR / "reference.step")
    args = parser.parse_args()

    for path in [args.reference]:
        if not path.exists():
            print(f"[ERROR] File not found: {path}")
            sys.exit(1)

    if not args.experiment.exists():
        print(f"[ERROR] Experiment file not found: {args.experiment}")
        print("       Run: freecadcmd freecad_build.py")
        sys.exit(1)

    results = measure(args.reference, args.experiment)

    # Save experiment geometry as _exp_geom.json for debugging
    exp_geom_path = SCRIPT_DIR / "_exp_geom.json"
    exp_geom = extract_geometry(args.experiment)
    with open(exp_geom_path, "w") as f:
        json.dump(exp_geom, f, indent=2)

    print("---")
    print(f"score:         {results['score']:.6f}")
    print(f"volume_sim:    {results['volume_sim']:.6f}")
    print(f"bbox_sim:      {results['bbox_sim']:.6f}")
    print(f"surface_sim:   {results['surface_sim']:.6f}")
    print(f"render_sim:    {results['render_sim']:.6f}")
    print("---")
    print(f"ref_volume:    {results.get('ref_volume', '?'):.2f}")
    print(f"exp_volume:    {results.get('exp_volume', '?'):.2f}")


if __name__ == "__main__":
    main()
