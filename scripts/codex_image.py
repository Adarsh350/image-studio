"""Free image generation and editing through the Codex CLI's built-in image tool, with a quality contract.

Runs `codex exec` on the ChatGPT login (~/.codex/auth.json): no API key, no
per-image billing, but each image draws on the ChatGPT message allowance.
Codex saves the PNG under ~/.codex/generated_images/<thread_id>/; this wrapper
finds it from the JSON event stream and copies it where you asked.

The quality contract (why this exists, not just a thin wrapper):
  1. lint(): a generate prompt must name the medium/camera, the light and the
     composition, and must not use slop words (stunning, 8k, cinematic...). A
     failing prompt raises before any quota is spent.
  2. The prompt is sent as a labelled spec (OpenAI's own gpt-image-2 guidance):
     use case, intended use, image roles, output size, the brief, then a fixed
     realism clause and a fixed exclusion clause that every image gets.
  3. Codex is told to pass the spec verbatim (no rewriting), at the largest
     valid size for the aspect and the highest quality the tool allows.
  4. --style-ref images are attached as labelled style anchors: match their
     realism, light and grade, never their content.

Binary: the VS Code extension's bundled codex, NOT the npm `codex` on PATH
(stale 0.114 on this machine). Override with CODEX_BIN. Model: CODEX_IMAGE_MODEL
(default gpt-5.6-luna; the image tool does not depend on the chat model).

    python -I codex_image.py --check                                     # offline tests + version, no quota
    python -I codex_image.py --lint "prompt"                             # lint only, no quota
    python -I codex_image.py --live "prompt" out.png [--aspect 4:5] [--ref edit-target.jpg] [--style-ref anchor.jpg ...] [--kind photo|illustration]
    python -I codex_image.py --batch jobs.json [--workers 3]
        jobs.json: [{"prompt": "...", "out": "a.png", "aspect": "4:5", "refs": ["in.jpg"],
                     "style_refs": ["anchor.jpg"], "kind": "photo"}, ...]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT = 420  # seconds; observed 35-60s at 1.5MP, larger sizes take longer

# Requested size per aspect (edges multiples of 16). Measured 2026-11-19: Codex's built-in image_gen
# ignores the size and returns ~1.5MP at the right aspect (4:5 -> 1122x1402). That covers 1080-wide
# feed/story crops at <=1x and a 1920x1080 cover at ~1.3x (under qa.py's 1.5x limit). The request is
# kept in case the tool starts honouring it; the result's `size` field reports what really came back.
SIZES = {
    "4:5": (1536, 1920), "1:1": (1600, 1600), "9:16": (1152, 2048), "16:9": (2048, 1152),
    "1.91:1": (2048, 1072), "3:2": (1920, 1280), "2:3": (1280, 1920), "4:3": (1792, 1344), "3:4": (1344, 1792),
}

# Words that summon the generic AI look. Whole-word, case-insensitive. Say what you see instead.
BANNED = [
    "stunning", "breathtaking", "epic", "masterpiece", "award-winning", "award winning", "beautiful",
    "gorgeous", "flawless", "perfect", "vibrant", "ultra-detailed", "ultra detailed", "highly detailed",
    "hyperrealistic", "hyper-realistic", "hyper realistic", "ultra realistic", "ultra-realistic", "4k", "8k",
    "hdr", "cinematic", "dramatic lighting", "volumetric", "god rays", "lens flare", "bokeh", "glow",
    "glowing", "neon", "holographic", "hologram", "futuristic", "sci-fi", "neural network", "digital brain",
    "robot", "cyborg", "teal and orange", "teal-and-orange", "purple gradient", "octane", "unreal engine",
    "artstation", "trending on", "diverse group", "thumbs up", "handshake", "pointing at", "magical",
    "dreamy", "ethereal", "surreal",
]
_BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b", re.I)

# A generate prompt must answer these three questions, or the model fills them with defaults (= slop).
REQUIRED = {
    "medium/camera (e.g. 'editorial photograph, 35mm lens, f/2.8')":
        r"\b(photo|photograph|photography|shot on|\d{2,3}\s?mm|lens|f/\d|illustration|illustrated|drawing|painting|vector)",
    "light (source, direction, time: 'soft window light from the left, late morning')":
        r"\b(light|lit|sun|sunlight|daylight|window|lamp|overcast|dusk|dawn|golden hour|shade|shadows?)\b",
    "composition (framing, subject position, negative space)":
        r"\b(close-up|close up|wide|medium shot|framing|framed|frame|overhead|top-down|eye-level|eye level|thirds?|negative space|composition|foreground|background|crop|angle|portrait orientation)\b",
}

REALISM = (
    "Photorealistic, indistinguishable from an unretouched frame from a professional editorial or "
    "documentary shoot on a full-frame camera. Real skin texture with pores, fine lines and natural "
    "unevenness; real fabric weave, creases and wear; real material grain, scuffs and everyday imperfection. "
    "True-to-life colour, natural contrast and white balance, gentle film-like grain. Anatomically correct "
    "people: natural proportions, five fingers per hand, relaxed natural poses and expressions, nobody "
    "looking into the lens unless the brief says so. Straight verticals and true perspective; light, "
    "shadows and reflections physically consistent with one believable light source."
)
ILLUSTRATION = (
    "Professional, hand-made-looking illustration in exactly the style the brief describes: consistent line "
    "weight, a limited palette, clean shapes, no gradients or effects the brief does not ask for."
)
EXCLUSIONS = (
    "Avoid: any text, letters, numbers, signage, labels, logos, brand marks, watermarks, signatures, frames "
    "or borders; readable screens or UI; stock-photo poses, forced smiles, people posing for the camera; "
    "airbrushed or waxy skin, plastic sheen, HDR look, glow or halos, oversaturated colour, heavy vignette; "
    "CGI or 3D-render look; spotless showroom perfection; perfect symmetry; extra or fused fingers, "
    "duplicated objects, warped straight lines, objects merging into each other, surreal or impossible details."
)

_INSTRUCTIONS = (
    "Call the built-in image generation tool (image_gen) now, exactly once. Use the SPEC below as the image "
    "prompt, word for word: do not rewrite, shorten, summarise or add to it. If the tool accepts size or "
    "quality settings, set size {w}x{h} and the highest quality. Do not read any files, skills or docs, "
    "and do not plan or explain. After the image is generated, reply with only the saved file path.\n\n"
    "SPEC:\n{spec}"
)


class CodexImageError(RuntimeError):
    pass


def lint(prompt: str, *, edit: bool = False) -> list[str]:
    """Problems that would make the image look generic. Empty list = OK. Edits only get the banned-word check."""
    problems = [f"banned word '{m.group(0)}' (describe what is literally in the frame instead)"
                for m in _BANNED_RE.finditer(prompt)]
    if not edit:
        problems += [f"missing {name}" for name, rx in REQUIRED.items() if not re.search(rx, prompt, re.I)]
        if len(prompt.split()) < 35:
            problems.append(f"too short ({len(prompt.split())} words): a usable brief is 50-120 words")
    return problems


def build_prompt(prompt: str, *, aspect: str, edit: bool = False, n_style: int = 0, kind: str = "photo") -> str:
    """The full message sent to Codex: instructions + labelled spec."""
    if aspect not in SIZES:
        raise CodexImageError(f"unknown aspect {aspect}; use one of {', '.join(SIZES)}")
    w, h = SIZES[aspect]
    roles = []
    if edit:
        roles.append("Image 1: the edit target, a real photo of the business.")
    first = 2 if edit else 1
    for i in range(first, first + n_style):
        roles.append(f"Image {i}: style reference only. Match its realism, light quality, colour grade, lens "
                     "character and grain. Do not copy its subject, people, objects, layout or setting.")
    lines = ["Use case: " + ("precise photo edit" if edit else
                             "photorealistic-natural" if kind == "photo" else "illustration"),
             "Intended use: production-ready marketing image for a real business's social media, website, "
             "Google Business Profile and ads. It must pass as a real photograph from a paid professional shoot "
             "and survive a full-screen look." if kind == "photo" else
             "Intended use: production-ready marketing illustration for a real business's social media and website."]
    if roles:
        lines.append("Images: " + " ".join(roles))
    lines.append(f"Output: {aspect} aspect ratio, {w}x{h} pixels, final-delivery quality.")
    if edit:
        lines.append("Edit (change only this): " + prompt.strip())
        lines.append("Keep unchanged: everything the edit does not name. People, faces, hands, products, "
                     "logos and the premises stay exactly as photographed. Same light, colour grade, grain, lens "
                     "and perspective as Image 1; any new area continues the real scene so the seam is invisible.")
        lines.append("Avoid: adding text, logos, watermarks or borders; restyling, smoothing skin, boosting "
                     "saturation or adding glow; inventing new people or objects the edit does not ask for.")
    else:
        lines.append("Brief: " + prompt.strip())
        lines.append("Constraints: " + (REALISM if kind == "photo" else ILLUSTRATION))
        lines.append(EXCLUSIONS)
    return _INSTRUCTIONS.format(w=w, h=h, spec="\n".join(lines))


def _codex_home() -> Path:
    return Path(os.getenv("CODEX_HOME") or Path.home() / ".codex")


def find_codex() -> Optional[str]:
    """CODEX_BIN, else the newest extension-bundled binary, else PATH."""
    explicit = os.getenv("CODEX_BIN")
    if explicit:
        return explicit
    exe = "codex.exe" if os.name == "nt" else "codex"
    found = list((Path.home() / ".vscode" / "extensions").glob(f"openai.chatgpt-*/bin/*/{exe}"))

    def version(p: Path) -> tuple:
        m = re.search(r"openai\.chatgpt-([\d.]+)", str(p))
        return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)

    if found:
        return str(max(found, key=version))
    return shutil.which("codex")  # may be stale; check() reports its version


def codex_version() -> Optional[str]:
    binary = find_codex()
    if not binary:
        return None
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


def generate(
    prompt: str,
    out_path: str,
    *,
    aspect: str = "16:9",
    refs: Optional[list[str]] = None,
    style_refs: Optional[list[str]] = None,
    kind: str = "photo",
    model: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Generate (or, with refs, edit) one image and write it to `out_path` (PNG). Uses ChatGPT quota.

    refs: at most one edit target (a real photo). style_refs: anchor photos for look only.
    Raises CodexImageError before spending quota if the prompt fails lint().
    """
    binary = find_codex()
    if not binary:
        raise CodexImageError("Codex not found. Install the OpenAI VS Code extension or set CODEX_BIN.")
    refs = [str(Path(r).resolve()) for r in refs or []]
    style_refs = [str(Path(r).resolve()) for r in style_refs or []]
    if len(refs) > 1:
        raise CodexImageError("one edit target per job; use style_refs for look references")
    for r in refs + style_refs:
        if not Path(r).is_file():
            raise CodexImageError(f"reference image not found: {r}")
    problems = lint(prompt, edit=bool(refs))
    if problems:
        raise CodexImageError("prompt failed lint: " + "; ".join(problems))
    text = build_prompt(prompt, aspect=aspect, edit=bool(refs), n_style=len(style_refs), kind=kind)
    cmd = [
        binary, "exec",
        "-m", model or os.getenv("CODEX_IMAGE_MODEL", DEFAULT_MODEL),
        "--skip-git-repo-check", "--ephemeral", "--json",
        "-c", "model_reasoning_effort=low",
    ]
    for r in refs + style_refs:  # order matters: Image 1 = edit target, then style refs
        cmd += ["-i", r]
    cmd.append("-")  # prompt on stdin, after -i (which takes multiple values)
    started = time.time()
    with tempfile.TemporaryDirectory() as cwd:  # empty cwd: nothing to load, nothing to write
        try:
            run = subprocess.run(cmd, input=text, capture_output=True, text=True,
                                 encoding="utf-8", timeout=timeout, cwd=cwd)
        except subprocess.TimeoutExpired as exc:
            raise CodexImageError(f"Codex image generation timed out after {timeout}s") from exc

    thread_id, reply, error = None, "", ""
    for line in run.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "thread.started":
            thread_id = ev.get("thread_id")
        elif ev.get("type") == "turn.failed":
            error = ev.get("error", {}).get("message", "turn failed")
        elif ev.get("item", {}).get("type") == "agent_message":
            reply = ev["item"].get("text", "")

    source: Optional[Path] = None
    if reply and Path(reply.strip()).is_file():
        source = Path(reply.strip())
    elif thread_id:
        pngs = sorted((_codex_home() / "generated_images" / thread_id).glob("*.png"))
        source = pngs[-1] if pngs else None
    if source is None:
        raise CodexImageError(error or f"Codex produced no image (exit {run.returncode}): {reply[:200] or run.stderr[-300:]}")

    dest = Path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    size = None
    try:
        from PIL import Image  # optional: report the real output size so the caller sees if size was honoured
        with Image.open(dest) as im:
            size = f"{im.width}x{im.height}"
    except Exception:
        pass
    return {"backend": "codex", "path": str(dest), "seconds": round(time.time() - started, 1),
            "thread_id": thread_id, "edit": bool(refs), "size": size}


def batch(jobs: list[dict[str, Any]], workers: int = 3) -> list[dict[str, Any]]:
    """Lint every job first (no quota spent if any fails), then run in parallel.
    A job that fails at generation reports its error instead of stopping the batch."""
    bad = {j["out"]: p for j in jobs if (p := lint(j["prompt"], edit=bool(j.get("refs"))))}
    if bad:
        return [{"path": out, "error": "prompt failed lint: " + "; ".join(p)} for out, p in bad.items()]

    def one(job: dict[str, Any]) -> dict[str, Any]:
        try:
            return generate(job["prompt"], job["out"], aspect=job.get("aspect", "16:9"), refs=job.get("refs"),
                            style_refs=job.get("style_refs"), kind=job.get("kind", "photo"))
        except CodexImageError as exc:
            return {"path": job["out"], "error": str(exc)}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, jobs))


def _self_test() -> None:
    good = ("Editorial photograph, 35mm lens at f/2.8, natural light. A dental hygienist in navy scrubs "
            "adjusts the overhead lamp above an empty treatment chair, her gloved hands on the handle. A "
            "small Dubai clinic room: pale oak cabinets, a steel instrument tray, a potted olive tree by the "
            "window. Soft late-morning daylight from a window on the left, gentle shadows. Medium shot at "
            "eye level, hygienist on the right third, clean wall in the upper left for a headline. Muted, "
            "true-to-life colour with sage-green and warm oak tones.")
    assert lint(good) == [], lint(good)
    slop = "A stunning futuristic dental clinic, cinematic lighting, 8k, ultra-detailed, glowing"
    found = lint(slop)
    for w in ("stunning", "futuristic", "cinematic", "8k", "ultra-detailed", "glowing", "missing light"):
        assert any(w in p for p in found), (w, found)
    assert any("too short" in p for p in found)
    assert lint("Extend the scene to the left to fill the frame", edit=True) == []
    assert lint("make it stunning", edit=True)
    assert "perfectly" not in str(lint(good + " The chairs sit perfectly aligned.")), "whole-word only"
    p = build_prompt(good, aspect="4:5", n_style=1)
    assert "1536x1920" in p and "Image 1: style reference" in p and "Avoid: any text" in p and good in p
    e = build_prompt("Remove the text overlay", aspect="16:9", edit=True, n_style=1)
    assert "Image 1: the edit target" in e and "Image 2: style reference" in e and "Keep unchanged" in e
    for a, (w, h) in SIZES.items():
        assert w % 16 == 0 and h % 16 == 0 and 655_360 <= w * h <= 8_294_400 and max(w, h) <= 3840, a
    try:
        build_prompt(good, aspect="5:7")
        raise AssertionError("unknown aspect should fail")
    except CodexImageError:
        pass
    print("self-test OK")


def _opt(args: list[str], name: str, default: Optional[str] = None) -> Optional[str]:
    return args[args.index(name) + 1] if name in args else default


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--live"] and len(args) >= 3:
        refs = [args[i + 1] for i, a in enumerate(args) if a == "--ref"]
        style = [args[i + 1] for i, a in enumerate(args) if a == "--style-ref"]
        try:
            print(json.dumps(generate(args[1], args[2], aspect=_opt(args, "--aspect", "16:9"), refs=refs,
                                      style_refs=style, kind=_opt(args, "--kind", "photo"))))
        except CodexImageError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args[:1] == ["--lint"] and len(args) >= 2:
        problems = lint(args[1], edit="--edit" in args)
        print("\n".join(problems) or "lint OK")
        sys.exit(1 if problems else 0)
    elif args[:1] == ["--batch"] and len(args) >= 2:
        results = batch(json.loads(Path(args[1]).read_text(encoding="utf-8")), int(_opt(args, "--workers", "3")))
        print(json.dumps(results, indent=2))
        sys.exit(1 if any("error" in r for r in results) else 0)
    elif args[:1] == ["--check"] or not args:
        _self_test()
        v = codex_version()
        print(f"codex: {find_codex()}\nversion: {v}")
        assert v and "0.114" not in v, "stale or missing Codex; install/update the OpenAI VS Code extension"
        print("OK")
    else:
        print(__doc__)
        sys.exit(2)
