---
name: image-studio
description: Turn a business website link into a ready-to-use set of marketing images. Reads the site, harvests its best existing photos, fixes the near-misses with Codex edits, generates whatever is missing with Codex (free, ChatGPT quota), rejects anything that looks like AI slop, and crops each image to the size it will be used at. Delivers exactly N images into a new folder in Downloads. Use for "/image-studio", "images for this site", "marketing images for <link>", "give me N images for this business", "social images from my website", "find the best images on this site", "make images for this brand", "edit these images for Instagram", or any request for a set of brand or marketing images (not video: that is creator-studio).
argument-hint: "<url> [count] [--use social|web|ads|mixed] [--existing-only]"
---

# Image Studio

Link in, N finished images out. `<skill-dir>` is this skill's base directory. First time on a
machine: `npm install` in `<skill-dir>` (Playwright; the Chromium it needs is shared with
creator-studio, else `npx playwright install chromium`). Needs Node 20+, Python 3.10+ with Pillow,
and the Codex CLI or the OpenAI VS Code extension signed in to ChatGPT.

Read these before writing the brief. The quality of the set is decided there.

- `<skill-dir>/references/playbook.md`: what to make. Placements and their specs, worked prompts
  for 12 business types, and the default mix for "N images".
- `<skill-dir>/references/craft.md`: how to make and judge each image. The brief template, the
  prompt recipe, style anchors and the three-pass reject gate.
- `<skill-dir>/references/industries/INDEX.md`: maps any business to one of 52 industry sections
  (benchmark brands, house style, slop tells, shot concepts, real-only shots), with a fallback for
  a business no section fits.

**The bar:** every delivered image can go straight into a paid ad or onto a client's Instagram
today. If it would look cheap next to the photos in `references/anchors/`, it isn't delivered.

## 1. Intake

Need three things: the **link**, the **count**, and the **use**. If the invocation gave all three,
don't ask. Otherwise ask once with AskUserQuestion, only for what is missing:

| Question | Options |
|---|---|
| How many images? | 6 · 10 · 20 (Other for any number) |
| What are they for? | Mixed social + web (Recommended) · Social posts · Website · Ads |

Defaults when the user says "just do it": 10 images, mixed. Whose brand: a client site gets no
Iyara context; Iyara's own site loads `iyara-labs` for the brief. If the count is over 20, say it
draws on the ChatGPT allowance (about 35s and one message per generated image, plus retries) and
continue.

**Sizes by use** (each slot gets one):

| Use | Size | Ratio |
|---|---|---|
| Feed post (Instagram, LinkedIn, Facebook) | 1080x1350 | 4:5 |
| Square post / profile tile | 1080x1080 | 1:1 |
| Story, Reel cover, TikTok | 1080x1920 | 9:16 |
| Website hero, blog header | 1920x1080 | 16:9 |
| Link preview (OG), ad landscape | 1200x630 | 1.91:1 |

Mixed set: use the default set in playbook.md section 4. It includes the Google Business Profile
slots, which take **real photos only** (Google's policy bars stock imagery, and a generated
photo of premises misrepresents them). If the site has no real photo for a GBP slot, the slot
becomes a feed post, and the reply lists the GBP shots the owner should take.

## 2. Read the site

```bash
W="$LOCALAPPDATA/image-studio/runs/<slug>-$(date +%Y-%m-%d-%H%M%S)"   # ~/.local/share/image-studio/runs on macOS/Linux
node <skill-dir>/scripts/harvest.mjs "<url>" "$W/site" --pages 6
```

Writes `site.json` (pages, headings, nav, meta, fonts, palette, every image with size and role),
`home.png` and `images/`. Then:

- Read `home.png` and the 6-10 largest `photo` images (contact sheet first:
  `python -I <skill-dir>/scripts/finish.py sheet "$W/site/sheet.jpg" <files>`).
- Write `$W/brief.md` per craft.md section 1.
- Sites behind bot protection or empty shells: say so, retry once with `--pages 1`, else ask for
  screenshots or a folder of images and continue from the brief.

## 3. Shot list

Find the business in `references/industries/INDEX.md` and read its section (INDEX.md says how to
use each part and what to do when nothing fits). Its House style goes into the brief and every
prompt; its Never list joins the reject gate; its Real only shots are never `generate`.

Write `$W/shots.md` per craft.md section 2, seeding concepts from the industry section's Shot
concepts and playbook.md section 3: N rows of `#, use, size, concept, source, ref`.
Post it in chat as a compact table and **carry on without waiting** (the user asked for a link-in,
files-out flow). `--existing-only` means no `generate` rows: if the site lacks N good photos,
deliver fewer and say how many it had.

Harvested images are good for `existing` only when all of these hold:

- they are photos, not graphics;
- they are sharp;
- they have no baked-in text;
- they are big enough that the final crop upscales 1.5x or less.

Mine big site photos before generating anything. One photo with a long side of 3000px or more
often holds two or three deliverables at its natural subject points: the wide scene, a person, a
detail. Each crop is its own `existing` row with its own `--focus`. Logos are never a slot.

## 4. Make

- **Existing:** straight to finishing.
- **Edit and generate:** write prompts per craft.md section 3 into `$W/jobs.json` and run all of
  them in one batch:

```bash
python -I <skill-dir>/scripts/codex_image.py --batch "$W/jobs.json" --workers 3
# jobs.json: [{"prompt": "...", "out": "<W>/raw/04a.png", "aspect": "4:5",
#               "style_refs": ["<skill-dir>/references/anchors/hands-craft-fresh-pasta.jpg"]},
#              {"prompt": "extend the scene left and right...", "out": "<W>/raw/07.png", "aspect": "16:9",
#               "refs": ["<W>/site/images/007.jpg"]}]
```

The script lints every prompt first and spends no quota if any prompt fails. It then wraps each
brief in Codex instructions: a labelled spec, the size for the aspect, the highest
quality, and the fixed realism and exclusion clauses. Anchors (`style_refs`) come from
`references/anchors/manifest.json`, by the shot's look first and the industry second (craft.md,
"Style anchors").

Make two candidates per `generate` slot so the gate has a choice: the same concept, one job with
`style_refs` and one without. Anchors pull the grade toward the site; the plain run often keeps
more fine detail. Tested 2026-11-19: each won one slot. If both candidates fail, rewrite the prompt. Ask Codex for the slot's own aspect: the built-in tool returns about 1.5MP at that aspect
whatever size is requested (4:5 comes back 1122x1402), which is enough for every slot up to a
1920x1080 cover. The result's `size` field shows what came back, and `qa.py` catches anything too
small.

No Codex (`codex_image.py --check` fails): don't use a paid image API. Fall back to
`--existing-only` and say so.

## 5. Gate

Run craft.md section 4 on every candidate:

1. `qa.py` (machine pass);
2. the contact sheet;
3. full size, with `finish.py zoom` on every hand, face and possible lettering.

Retry rejects as the gate says: rewrite once, try a new concept once, then fall back to the
next-best harvested photo. After finishing, run `qa.py` once more on `final/` at each delivery
size (it takes file paths, not a folder: `qa.py "$W"/final/0[1-5]-*.jpg --size 1080x1350`), and
look at the final contact sheet as one set.

## 6. Finish and deliver

```bash
python -I <skill-dir>/scripts/finish.py fit <source> "$W/final/01-feed-<concept>.jpg" --size 1080x1350 --focus 0.5,0.4
```

Pick `--focus` from what you saw (the subject's position, as fractions of width and height). The
script warns above a 1.5x upscale: then pick another source or regenerate, don't ship it soft.

- **Deliver:** copy `final/` to `~/Downloads/<slug>-images-<YYYY-MM-DD>/` (add `-2`, `-3` if it
  exists). Exactly N images, named `NN-<use>-<concept>.jpg`. Nothing else in that folder.
- **Chat reply:** the folder path; a table of `file, size, source (site page URL / Codex edit /
  Codex generated)`; anything the user should check (an edited real photo, a slot that fell back);
  the real-only and GBP shots the site lacked, as a short list for the owner to take; and the work
  dir for re-rolls.
- **Rights:** images harvested from a site may be licensed stock that is cleared for that website
  only. Say so in one line when the site isn't the user's own or the set includes harvested photos.
- **Re-rolls** ("redo 04", "warmer", "two more"): reuse the latest work dir for that slug, change
  only those slots, overwrite them in the same Downloads folder.
- **Prune** at the start of each run: `find "$LOCALAPPDATA/image-studio/runs" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +`

## Hard rules

- Never generate the client's logo, product as sold, team, premises, certificates or screenshots.
  Those come from the site or from the user.
- Google Business Profile slots are real photos only.
- Never put text, lettering or logos in a generated image.
- Never ship an image that failed the gate to make up the count. Deliver fewer and say why.
- Paid tools need a flag first: the Higgsfield MCP, any image API other than Codex, any paid
  upscaler.

## Related skills

- `creator-studio`: WHEN the ask is a video. It can take this skill's finished images as stills.
- `social` / `instagram-content` / `linkedin-content`: WHEN the images need captions and a
  posting plan. They consume the Downloads folder this skill writes.
- `brand`: WHEN the site has no usable visual identity and one has to be defined first.

## Self-tests

`node scripts/harvest.mjs --self-test` · `python -I scripts/finish.py --self-test` ·
`python -I scripts/qa.py --self-test` · `python -I scripts/codex_image.py --check` (lint and prompt tests
plus the Codex version; no quota used). All at once: `npm run check`.
