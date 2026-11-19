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
    python -I finish.py --self-test
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

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
    elif a[:1] == ["sheet"] and len(a) >= 3:
        sheet(a[1], a[2:])
        print(a[1])
    else:
        print(__doc__)
        sys.exit(2)
