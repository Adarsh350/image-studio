"""Automatic quality checks for a candidate set, run before anyone looks at it.

    python -I qa.py <img> [<img> ...] [--size 1080x1350] [--json]
    python -I qa.py --self-test

Per image (against --size, the delivery size; default 1080x1080):
  FAIL upscale   the source is too small: the delivery crop would upscale it more than 1.5x
  FAIL dup       a near-duplicate of another image in the set (perceptual dHash, Hamming <= 6 of 64)
  WARN soft      low detail (variance of the Laplacian at delivery scale is low): check focus at full size
  WARN saturated many strongly saturated pixels: the "AI candy" grade
  WARN clipped   blown highlights or crushed shadows across a large area
  WARN flat      almost no tonal range (a blank or washed-out frame)
FAIL = drop it or fix it. WARN = look at that image at full size before passing it.
Exit code 1 if anything FAILs. Thresholds are deliberately loose: this catches the obvious,
the visual review in craft.md catches the rest.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

MAX_UPSCALE = 1.5
DUP_BITS = 6
SOFT_LAPLACIAN = 40.0      # variance of the Laplacian on grey 0-255 at delivery scale
SAT_PIXEL, SAT_SHARE = 0.80, 0.12
CLIP_SHARE = 0.04
FLAT_STD = 18.0


def dhash(im: Image.Image) -> int:
    g = np.asarray(im.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def laplacian_var(grey: np.ndarray) -> float:
    g = grey.astype(np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def check(path: str, size: tuple[int, int]) -> dict:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = size
    scale = max(w / im.width, h / im.height)
    # judge sharpness and tone at the size it will actually be seen
    seen = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS) if scale < 1 else im
    grey = np.asarray(seen.convert("L"))
    hsv = np.asarray(seen.convert("HSV"), dtype=np.float32) / 255.0
    rgb = np.asarray(seen)
    sharp = laplacian_var(grey)
    sat_share = float(((hsv[..., 1] > SAT_PIXEL) & (hsv[..., 2] > 0.25)).mean())
    hi = float((rgb.min(axis=2) >= 250).mean())
    lo = float((rgb.max(axis=2) <= 5).mean())
    std = float(grey.std())
    issues = []
    if scale > MAX_UPSCALE:
        issues.append(f"FAIL upscale {scale:.2f}x (source {im.width}x{im.height} for {w}x{h})")
    if sharp < SOFT_LAPLACIAN:
        issues.append(f"WARN soft (laplacian {sharp:.0f} < {SOFT_LAPLACIAN:.0f})")
    if sat_share > SAT_SHARE:
        issues.append(f"WARN saturated ({sat_share:.0%} of pixels strongly saturated)")
    if hi > CLIP_SHARE or lo > CLIP_SHARE:
        issues.append(f"WARN clipped (highlights {hi:.0%}, shadows {lo:.0%})")
    if std < FLAT_STD:
        issues.append(f"WARN flat (tonal std {std:.0f})")
    return {"file": path, "source": f"{im.width}x{im.height}", "upscale": round(scale, 2),
            "sharpness": round(sharp), "saturated": round(sat_share, 3), "hash": dhash(im), "issues": issues}


def run(paths: list[str], size: tuple[int, int]) -> list[dict]:
    results = [check(p, size) for p in paths]
    for i, a in enumerate(results):
        for b in results[i + 1:]:
            d = bin(a["hash"] ^ b["hash"]).count("1")
            if d <= DUP_BITS:
                b["issues"].append(f"FAIL dup of {Path(a['file']).name} (hash distance {d})")
    return results


def _self_test() -> None:
    rng = np.random.default_rng(7)
    with tempfile.TemporaryDirectory() as d:
        base = np.full((1400, 1400, 3), 110, np.uint8)
        for k in range(40):  # sharp, varied, natural-ish scene: random rectangles + noise
            x, y = rng.integers(0, 1300, 2)
            base[y:y + rng.integers(40, 300), x:x + rng.integers(40, 300)] = rng.integers(40, 200, 3)
        base = np.clip(base.astype(int) + rng.normal(0, 12, base.shape), 0, 255).astype(np.uint8)
        Image.fromarray(base).save(f"{d}/sharp.png")
        Image.fromarray(base).filter(ImageFilter.GaussianBlur(12)).save(f"{d}/soft.png")
        Image.fromarray(base).resize((1200, 1200)).save(f"{d}/dup.png")
        Image.fromarray(base[:600, :600]).save(f"{d}/small.png")
        candy = np.zeros((1200, 1200, 3), np.uint8)
        candy[..., 0], candy[..., 2] = 255, rng.integers(0, 60, (1200, 1200))
        Image.fromarray(candy).save(f"{d}/candy.png")
        Image.fromarray(np.full((1200, 1200, 3), 128, np.uint8)).save(f"{d}/flat.png")
        r = {Path(x["file"]).stem: x["issues"] for x in
             run([f"{d}/{n}.png" for n in ("sharp", "soft", "dup", "small", "candy", "flat")], (1080, 1080))}
        assert r["sharp"] == [], r["sharp"]
        assert any("soft" in i for i in r["soft"]), r["soft"]
        assert any("FAIL dup of sharp" in i for i in r["dup"]), r["dup"]
        assert any("FAIL upscale" in i for i in r["small"]), r["small"]
        assert any("saturated" in i for i in r["candy"]), r["candy"]
        assert any("flat" in i for i in r["flat"]), r["flat"]
    print("self-test OK")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--self-test"]:
        _self_test()
        sys.exit(0)
    size = (1080, 1080)
    if "--size" in a:
        sw, sh = a[a.index("--size") + 1].split("x")
        size = (int(sw), int(sh))
        del a[a.index("--size"):a.index("--size") + 2]
    as_json = "--json" in a
    files = [x for x in a if x != "--json"]
    if not files:
        print(__doc__)
        sys.exit(2)
    res = run(files, size)
    if as_json:
        print(json.dumps([{k: v for k, v in r.items() if k != "hash"} for r in res], indent=2))
    else:
        for r in res:
            print(f"{Path(r['file']).name}: {r['source']} upscale {r['upscale']}x sharp {r['sharpness']}  "
                  + ("; ".join(r["issues"]) or "ok"))
    sys.exit(1 if any(i.startswith("FAIL") for r in res for i in r["issues"]) else 0)
