# Craft: briefs, prompts and the reject gate

The gap between "AI slop" and an image a business can use is almost never the model. It is a
vague prompt and no one saying no. This file is both halves.

## 1. The brand brief (write before any shot list)

Fill `brief.md` in the work dir from `site.json`, `home.png` and the best harvested photos. Keep
it to these lines; each one changes what goes into a prompt.

- **Business:** what they sell, to whom, in one sentence, quoted from their own headings.
- **Place:** city and setting the customers live in (light, architecture, climate, dress). A Dubai
  clinic does not get a Scandinavian loft.
- **Customers:** age range, life stage, cultural mix as the site shows or implies. Never default to
  one demographic.
- **Existing visual language:** photographic or illustrated; warm or cool; airy or moody; candid or
  posed; flat-lay, people or environment. Generated shots must sit beside these without a seam.
- **Palette:** the 3-4 brand hexes from `site.palette` that are not near-white or near-black, named
  as everyday objects in prompts ("a deep forest-green ceramic mug"), never as hex codes.
- **Real, never generated:** the logo, the product as sold, named team members, the premises,
  screenshots, certificates, client logos. List what the site actually shows.
- **Tone words:** two or three, taken from the copy (e.g. "calm, clinical, reassuring").

## 2. The shot list

One row per output image: `#, use, size, concept, source, ref`. Rules:

- **Source order:** `existing` (a harvested photo that is good and big enough) beats `edit` (a
  harvested photo fixed by Codex: wrong aspect, clutter, a stray overlay) beats `generate`.
- **Variety across the set:** mix wide, medium and detail; people and no people; interior,
  exterior and object. No two rows with the same subject and framing.
- **Every concept is something the business really does or a moment its customer really has.**
  "Hands working on a laptop" is filler; "a technician reading a pressure gauge on a rooftop AC
  unit at dusk" is a shot.
- **No text in images.** Headlines get set later in a design tool, so leave clean space instead
  (say where: "empty sky in the upper third").

## 3. Writing the prompt

Write it like a photographer's brief, in this order, in plain sentences:

1. **Medium and camera:** "Editorial photograph, 35mm lens, f/2.8, natural light" (or the
   illustration style the site uses, described precisely).
2. **Subject doing something:** who, what exactly, mid-action. People are ordinary-looking, real
   ages, not looking at the camera, hands busy or out of frame.
3. **Setting with specifics:** place, materials, two or three concrete props that belong there,
   some lived-in wear.
4. **Light:** source, direction and time ("low late-afternoon sun from the left through blinds").
5. **Composition:** framing, where the subject sits, where the negative space is.
6. **Colour:** grade and the palette objects; "muted, true-to-life colour".
7. **Exclusions** are added for you: `codex_image.py` wraps every brief in a labelled spec with a
   fixed realism clause (real skin, fabric and material texture, true-to-life colour, five fingers,
   straight verticals, one consistent light source) and a fixed exclusion clause (no text, logos,
   watermarks, stock poses, HDR, glow, CGI look). Don't repeat them; spend the words on 1-6.

Aim for 50-120 words. `codex_image.py` lints every generate prompt before spending quota: it
refuses prompts that miss a medium or camera, a light or a composition, that run under 35 words, or
that use a banned word (`BANNED` in the script: stunning, epic, 8k, hyperrealistic, cinematic,
futuristic, glowing, neon, bokeh, vibrant, perfect, handshake, diverse group and others). Check a
prompt for free with `python -I <skill-dir>/scripts/codex_image.py --lint "<prompt>"`. Ideas the
linter can't catch are banned too: a handshake over a globe, floating UI, a digital brain, a
purple-blue gradient, studio-white everything, smiling professionals in a row, anyone pointing at a
screen.

Copy the shape of the worked prompts in `playbook.md` section 3. They pass the lint and they read
like a photographer's brief.

### Style anchors (`style_refs`)

Attach one or two anchor photos to one of each slot's two candidates; the other runs plain
(SKILL.md step 4). Pick anchors by **look**, not subject. `references/anchors/manifest.json` tags
each of the 69 anchors with a look (`interior-daylight`, `hands-craft`, `people-candid`,
`food-table`, `exterior-place`, `portrait-environmental`, `product-surface`, `moody-low-light`)
and the industry sections it suits. Among anchors with the right look, prefer one tagged for the
business's industry. Codex is told to match the anchor's realism, light, grade and grain and to
copy nothing in it. All anchors are CC0 or Pexels-licensed and were viewed before they were added;
add new ones the same way (view at full size, record source, creator and licence in the manifest).

When the site has its own good photos, a harvested photo is the better anchor: the new image then
grades like the site. Never anchor on an image you would reject.

### Edits (`--ref`)

Use for: extending a harvested photo to a new aspect ("extend the scene to the left and right to
fill a 16:9 frame, continue the floor and wall naturally"), removing an overlay or text, cleaning a
distracting background, relighting slightly. One change per edit. Never alter the product, a face,
or the logo: if the instruction would change a real thing, it is not an edit job.

## 4. The reject gate

Three passes, in this order:

1. **Machine pass:**
   `python -I <skill-dir>/scripts/qa.py <candidates> --size <delivery WxH>`. A `FAIL` (needs more
   than a 1.5x upscale, or a near-duplicate) is out. Each `WARN` names something to check at full
   size in pass 3.
2. **Sheet pass:** a contact sheet of every candidate, for the things you only see side by side:
   a grade that drifts, a repeated composition, a set that is all people or all objects.
3. **Full-size pass:** Read each survivor at full size. Then zoom on every region where the
   generator usually fails, at native pixels:
   `python -I <skill-dir>/scripts/finish.py zoom <img> <out.png> --box x0,y0,x1,y1`.
   - Zoom on every hand and every face.
   - Zoom on anywhere that lettering could appear: signs, screens, packaging, paper, clothing.
   - Zoom on the busiest corner of the background.
   A defect you only find at native pixels is still a defect: the image will be seen full-screen
   on a phone.

Reject on any one of these:

**Defects:** extra, fused or missing fingers; odd teeth or eyes; limbs that don't connect; any
pseudo-text or warped lettering; straight lines that bend (door frames, shelves, tiles); objects
melting into each other; duplicated objects; impossible scale; inconsistent shadows; a watermark
or border.

**Slop tells:** waxy or airbrushed skin; HDR glow or halos; oversaturation; everything spotless
and symmetrical; a stock pose; a subject dead-centre for no reason; a plastic sheen on materials;
a background that dissolves into mush.

**Brand misses:** wrong place or culture; off-palette; contradicts what the business does; shows a
product, person or premises that could be mistaken for the real one; would look out of place next
to the site's own photos.

**Set misses:** two near-duplicates; one image graded differently from the rest; the set is all
people or all objects.

Then score what survives 1-5 on three questions:

- **Realism:** would a photographer believe it was shot?
- **Brand fit:** does it sit beside the site's own photos and the anchors without a seam?
- **Usefulness:** could a marketer drop it into a post today?

Ship only images that score 4+ on all three. Hold it to the anchors: an image that would look
cheap next to them is a 3. A reject gets one rewritten prompt that
names the failure ("hands out of frame", "light from a single window, no glow"), then a second
attempt with a different concept, then the slot falls back to the next-best harvested photo.
Never ship a known defect to make the count.
