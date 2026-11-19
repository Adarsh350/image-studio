"""Finish images for delivery, and build contact sheets for QA.

    python -I finish.py fit <in> <out.jpg> --size 1080x1350 [--focus 0.5,0.4]
        Cover-fit: scale to fill the target, crop around the focus point (x,y in 0-1, default
        centre), save sRGB JPEG q92 without metadata (or PNG when <out> ends in .png). Prints the
        upscale factor; above 1.5x it warns, because detail will be soft.
    python -I finish.py sheet <out.jpg> <img> [<img> ...]
        Labelled grid of thumbnails (filename under each), for one-look QA of a whole set.
    python -I finish.py zoom <in> <out.png> --box 0.3,0.4,0.7,0.9
        Crop a region (x0,y0,x1,y1 as fractions) at native resolution, no resize, so hands, faces,
        teeth and fine edges can be inspected pixel-true before an image is passed.
    python -I finish.py screen <scene> <capture> <out> [--aspect 16:10] [--tol 70]
        Put a real capture on a generated device: <scene> has a screen of flat pure green
        (#00FF00); the green area is found, the capture is cropped to the screen's aspect
        (top-aligned) and perspective-warped onto it. Prints the corners it found.
    python -I finish.py --self-test
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

WARN_UPSCALE = 1.5


def fit(src: str, dst: str, size: tuple[int, int], focus: tuple[float, float] = (0.5, 0.5)) -> float:
    w, h = size
    im = ImageOps.exif_transpose(Image.open(src))
    has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
    im = im.convert("RGBA" if has_alpha and dst.lower().endswith(".png") else "RGB")
    scale = max(w / im.width, h / im.height)
    rw, rh = round(im.width * scale), round(im.height * scale)
    im = im.resize((rw, rh), Image.LANCZOS)
    left = min(max(round(rw * focus[0] - w / 2), 0), rw - w)
    top = min(max(round(rh * focus[1] - h / 2), 0), rh - h)
    im = im.crop((left, top, left + w, top + h))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    if dst.lower().endswith(".png"):
        im.save(dst, optimize=True)
    else:
        im.save(dst, quality=92, optimize=True, progressive=True, subsampling=0)
    return scale


def sheet(dst: str, files: list[str], thumb: int = 360, cols: int = 4) -> None:
    pad, label = 12, 22
    rows = -(-len(files) // cols)
    canvas = Image.new("RGB", (cols * (thumb + pad) + pad, rows * (thumb + pad + label) + pad), "#1b1b1b")
    draw = ImageDraw.Draw(canvas)
    for i, f in enumerate(files):
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((thumb, thumb), Image.LANCZOS)
        x = pad + (i % cols) * (thumb + pad)
        y = pad + (i // cols) * (thumb + pad + label)
        canvas.paste(im, (x + (thumb - im.width) // 2, y + (thumb - im.height) // 2))
        draw.text((x, y + thumb + 4), f"{Path(f).name}  {Image.open(f).size[0]}x{Image.open(f).size[1]}", fill="#e8e8e8")
    canvas.save(dst, quality=88)


def zoom(src: str, dst: str, box: tuple[float, float, float, float]) -> tuple[int, int]:
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    x0, y0, x1, y1 = box
    crop = im.crop((round(x0 * im.width), round(y0 * im.height), round(x1 * im.width), round(y1 * im.height)))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    crop.save(dst)
    return crop.size


def _solve(m: list[list[float]], v: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (the 8x8 perspective system; no numpy needed)."""
    n = len(v)
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-12:
            raise ValueError("degenerate quad: the corners are collinear")
        a[c], a[p] = a[p], a[c]
        for r in range(n):
            if r != c and a[r][c]:
                f = a[r][c] / a[c][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[i][n] / a[i][i] for i in range(n)]


def _perspective(dst_pts, src_pts) -> list[float]:
    """Image.transform(PERSPECTIVE) coefficients mapping each output point in dst_pts to src_pts."""
    m, v = [], []
    for (x, y), (u, w) in zip(dst_pts, src_pts):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); v.append(u)
        m.append([0, 0, 0, x, y, 1, -w * x, -w * y]); v.append(w)
    return _solve(m, v)


def _green_mask(im: Image.Image, tol: int) -> Image.Image:
    r, g, b = im.convert("RGB").split()
    return ImageChops.subtract(g, ImageChops.lighter(r, b)).point(lambda d: 255 if d > tol else 0)


def find_screen(im: Image.Image, tol: int = 70) -> tuple[list[tuple[int, int]], Image.Image]:
    """Corners (TL, TR, BR, BL) of the green screen, and its mask. Raises if there is no clean quad."""
    mask = _green_mask(im, tol)
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError("no green screen found (generate the device with a flat pure-green #00FF00 screen)")
    x0, y0, x1, _ = bbox
    w = x1 - x0
    best = [(-1e18, (0, 0))] * 4  # extremes of -(x+y), x-y, x+y, y-x -> TL, TR, BR, BL
    n = 0
    for i, on in enumerate(mask.crop(bbox).tobytes()):  # L mode: one byte per pixel
        if not on:
            continue
        n += 1
        x, y = x0 + i % w, y0 + i // w
        for k, sc in enumerate((-(x + y), x - y, x + y, y - x)):
            if sc > best[k][0]:
                best[k] = (sc, (x, y))
    quad = [pt for _, pt in best]
    area = abs(sum(quad[i][0] * quad[i - 1][1] - quad[i - 1][0] * quad[i][1] for i in range(4))) / 2
    if n < 0.002 * im.width * im.height or not area or n / area < 0.8:
        raise ValueError(f"the green area is not one clean screen ({n} px, {n / area if area else 0:.2f} of its quad); regenerate")
    return quad, mask


def screen(scene: str, capture: str, dst: str, aspect: float | None = None, tol: int = 70) -> list[tuple[int, int]]:
    bg = ImageOps.exif_transpose(Image.open(scene)).convert("RGB")
    quad, mask = find_screen(bg, tol)
    tl, tr, br, bl = quad
    d = lambda p, q: ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
    aspect = aspect or (d(tl, tr) + d(bl, br)) / (d(tl, bl) + d(tr, br))
    cap = ImageOps.exif_transpose(Image.open(capture)).convert("RGB")
    if cap.width / cap.height > aspect:  # wider than the screen: trim the sides evenly
        cw = round(cap.height * aspect)
        cap = cap.crop(((cap.width - cw) // 2, 0, (cap.width - cw) // 2 + cw, cap.height))
    else:  # taller: keep the top of the page
        cap = cap.crop((0, 0, cap.width, round(cap.width / aspect)))
    # Pad by replicating the edges so pixels just outside the quad (the dilated mask, rounded
    # screen corners) pick up the page's edge colour instead of black.
    pad = max(4, round(0.03 * max(cap.size)))
    padded = Image.new("RGB", (cap.width + 2 * pad, cap.height + 2 * pad))
    for box, src in (((0, 0, padded.width, pad), (0, 0, cap.width, 1)),
                     ((0, pad + cap.height, padded.width, padded.height), (0, cap.height - 1, cap.width, cap.height)),
                     ((0, 0, pad, padded.height), (0, 0, 1, cap.height)),
                     ((pad + cap.width, 0, padded.width, padded.height), (cap.width - 1, 0, cap.width, cap.height))):
        padded.paste(cap.crop(src).resize((box[2] - box[0], box[3] - box[1])), box[:2])
    padded.paste(cap, (pad, pad))
    src_pts = [(pad, pad), (pad + cap.width, pad), (pad + cap.width, pad + cap.height), (pad, pad + cap.height)]
    warped = padded.transform(bg.size, Image.PERSPECTIVE, _perspective(quad, src_pts), Image.BICUBIC)
    alpha = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1))  # covers the green fringe
    out = Image.composite(warped, bg, alpha)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, **({} if dst.lower().endswith(".png") else {"quality": 92, "subsampling": 0}))
    return quad


def _self_test() -> None:
    with tempfile.TemporaryDirectory() as d:
        src = f"{d}/src.png"
        im = Image.new("RGB", (1200, 800), "white")
        ImageDraw.Draw(im).rectangle((900, 0, 1199, 799), fill="red")  # red band on the right
        im.save(src)
        s = fit(src, f"{d}/right.jpg", (800, 800), (1.0, 0.5))
        out = Image.open(f"{d}/right.jpg")
        assert out.size == (800, 800), out.size
        assert out.getpixel((790, 400))[0] > 200 and out.getpixel((790, 400))[1] < 60, "focus right should keep red band"
        assert abs(s - 1.0) < 1e-6, s
        s = fit(src, f"{d}/big.jpg", (1920, 1080))
        assert Image.open(f"{d}/big.jpg").size == (1920, 1080) and s == 1.6, s
        sheet(f"{d}/sheet.jpg", [f"{d}/right.jpg", f"{d}/big.jpg", src])
        assert Image.open(f"{d}/sheet.jpg").width > 1000
        assert zoom(src, f"{d}/z.png", (0.75, 0.0, 1.0, 0.5)) == (300, 400)
        assert Image.open(f"{d}/z.png").getpixel((150, 200))[0] > 200, "zoom should land on the red band"
        # screen: a tilted green quad on grey; the capture's red corner must land top-left, blue bottom-right.
        quad = [(200, 120), (620, 160), (600, 470), (180, 420)]
        scene = Image.new("RGB", (800, 600), (90, 90, 90))
        ImageDraw.Draw(scene).polygon(quad, fill=(0, 255, 0))
        scene.save(f"{d}/scene.png")
        cap = Image.new("RGB", (1600, 1200), "white")
        ImageDraw.Draw(cap).rectangle((0, 0, 799, 599), fill="red")
        ImageDraw.Draw(cap).rectangle((800, 600, 1599, 1199), fill="blue")
        cap.save(f"{d}/cap.png")
        found = screen(f"{d}/scene.png", f"{d}/cap.png", f"{d}/screen.png", aspect=4 / 3)
        assert all(abs(a - b) <= 2 for p, q in zip(found, quad) for a, b in zip(p, q)), found
        res = Image.open(f"{d}/screen.png").convert("RGB")
        assert res.getpixel((230, 160))[0] > 200 and res.getpixel((230, 160))[2] < 60, "top-left should be red"
        assert res.getpixel((570, 430))[2] > 200 and res.getpixel((570, 430))[0] < 60, "bottom-right should be blue"
        assert _green_mask(res, 70).getbbox() is None, "no green may survive"
        coeffs = _perspective(quad, [(0, 0), (1, 0), (1, 1), (0, 1)])
        x, y = quad[2]
        den = coeffs[6] * x + coeffs[7] * y + 1
        assert abs((coeffs[0] * x + coeffs[1] * y + coeffs[2]) / den - 1) < 1e-9
        try:
            screen(f"{d}/cap.png", f"{d}/cap.png", f"{d}/x.png")
            raise AssertionError("a scene without green must be refused")
        except ValueError:
            pass
    print("self-test OK")


def _parse_pair(text: str, sep: str, cast=float) -> tuple:
    a, b = text.split(sep)
    return cast(a), cast(b)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--self-test"]:
        _self_test()
    elif a[:1] == ["fit"] and len(a) >= 3 and "--size" in a:
        size = _parse_pair(a[a.index("--size") + 1], "x", int)
        focus = _parse_pair(a[a.index("--focus") + 1], ",") if "--focus" in a else (0.5, 0.5)
        scale = fit(a[1], a[2], size, focus)
        print(f"{a[2]} {size[0]}x{size[1]} upscale {scale:.2f}x" + ("  WARNING: soft, source too small" if scale > WARN_UPSCALE else ""))
    elif a[:1] == ["zoom"] and len(a) >= 3 and "--box" in a:
        box = tuple(float(v) for v in a[a.index("--box") + 1].split(","))
        print(a[2], "%dx%d" % zoom(a[1], a[2], box))
    elif a[:1] == ["screen"] and len(a) >= 4:
        asp = _parse_pair(a[a.index("--aspect") + 1], ":") if "--aspect" in a else None
        quad = screen(a[1], a[2], a[3], asp[0] / asp[1] if asp else None,
                      int(a[a.index("--tol") + 1]) if "--tol" in a else 70)
        print(a[3], "screen corners TL,TR,BR,BL:", quad)
    elif a[:1] == ["sheet"] and len(a) >= 3:
        sheet(a[1], a[2:])
        print(a[1])
    else:
        print(__doc__)
        sys.exit(2)
