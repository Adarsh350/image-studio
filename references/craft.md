# Craft: briefs, prompts and the reject gate

The gap between "AI slop" and an image a business can use is almost never the model. It is a
vague prompt and no one saying no. This file is both halves.

## 1. The brand brief (write before any shot list)

Fill `brief.md` in the work dir from `site.json`, `home.png` and the best harvested photos. Keep
it to these lines; each one changes what goes into a prompt.

- **Business:** what they sell, to whom, in one sentence, quoted from their own headings.
- **Offers and proof:** one line per service line or product range. For each one, say what the
  work looks like as an image (a finished client website, a dashboard, a plated dish, a fitted
  kitchen), then where the real proof is:
  - case-study or client-site URLs, from `site.json` `pages[].outbound` and the site's work pages;
  - UI or demo elements on its own pages, from `pages[].ui` (selector plus hint);
  - metrics quoted from the site, word for word, with the page they came from;
  - screenshots the user supplied (`--proof`).
  An offer with no proof is still listed, marked "no proof": the reply asks the owner for it.
- **Place:** city and setting the customers live in (light, architecture, climate, dress). A Dubai
  clinic does not get a Scandinavian loft.
- **Customers:** age range, life stage, cultural mix as the site shows or implies. Never default to
  one demographic.
- **Existing visual language:** photographic or illustrated; warm or cool; airy or moody; candid or
  posed; flat-lay, people or environment. Generated shots must sit beside these without a seam.
- **Palette:** the 3-4 brand hexes from `site.palette` that are not near-white or near-black, named
  as everyday objects in prompts ("a deep forest-green ceramic mug"), never as hex codes.
- **Real, never generated:** the logo, the product as sold, named team members, the premises,
  screenshots and product UI, certificates, client logos. List what the site actually shows.
  Screens and UI are captured (`capture.mjs`) or supplied, never generated.
- **Tone words:** two or three, taken from the copy (e.g. "calm, clinical, reassuring").

## 2. The shot list

One row per output image: `#, use, size, shows, concept, source, ref`. `shows` names the offer
from the brief the image proves, or `mood` for a brand or atmosphere slot. Rules:

- **Showcase first.** A showcase slot shows what the business sells: the product, the finished
  work, the result, or the service being delivered. A mood slot shows the brand's world: the
  place, the people at work, a detail. At least 60% of N (round up) are showcase slots. Mood slots
  are capped at 40%. Every offer in the brief gets at least one showcase slot when N allows; when
  it doesn't, the flagship offer and the best-proved ones go first. For a restaurant or a shop the
  product photos are already showcase; for a web, software or service business they almost never
  are, so the showcase comes from proof.
- **Source order for showcase slots:**
  1. `proof`: a screenshot the user supplied;
  2. `capture`: a real screenshot made with `capture.mjs`;
  3. `mockup`: captures framed by `mockup.mjs` (browser, phone, pair, before/after, element);
  4. `screen`: a generated device scene with the capture composited on its screen (`finish.py screen`);
  5. `existing` and `edit`;
  6. `generate`, only for a physical product or service that can honestly be shown without the
     real thing (a generic dish, a generic trade at work). Never for a screen, UI, dashboard,
     client site, AI answer or metric.
- **Source order for mood slots:** `existing` (a harvested photo that is good and big enough)
  beats `edit` (a harvested photo fixed by Codex: wrong aspect, clutter, a stray overlay) beats
  `generate`.
- **Variety across the set:** mix wide, medium and detail; people and no people; interior,
  exterior and object. No two rows with the same subject and framing.
- **Every concept is something the business really does or a moment its customer really has.**
  "Hands working on a laptop" is filler; "a technician reading a pressure gauge on a rooftop AC
  unit at dusk" is a shot.
- **No generated text.** Codex never draws words, numbers, UI or screens; headlines get set later
  in a design tool, so leave clean space instead (say where: "empty sky in the upper third").
  Real pixels are different: a capture, a supplied screenshot and the site's own copy may carry
  text, because it is the business's real text.
- **Captures for portrait slots:** a desktop viewport is landscape, so a 4:5 or 9:16 browser
  mockup of it leaves a lot of empty ground. Use `--full` (the whole page, top-aligned in the
  window), a `phone` or `pair` layout, or an `element` capture.

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

### Screen scenes (`source: screen`)

To put a real capture into a photographed scene (a laptop on a client's desk, a phone in a hand),
generate the scene with an empty screen, then composite the capture onto it:

1. Write a normal photographer's brief for the scene and describe the screen as "the screen shows
   a flat, uniform pure green (#00FF00) field edge to edge, no content, no reflections". Keep the
   screen facing the camera at a modest angle, unobstructed (no hand or cup over it), and at least
   a fifth of the frame wide, so the capture stays readable.
2. Ask for the device's real aspect: laptops 16:10, phones about 9:19.5.
3. `python -I <skill-dir>/scripts/finish.py screen <scene.png> <capture.png> <out.png> [--aspect 16:10]`
   finds the green, crops the capture to fit (top-aligned) and warps it onto the screen. It refuses
   a scene whose green is missing or not one clean quad: regenerate rather than patch.
4. Gate the result like any other image, plus the capture misses in section 4.

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
   `python -I <skill-dir>/scripts/finish.py zoom <img> <out.png> --box x0,y0,x1,y1`
   (fractions of width and height, 0-1, not pixels; pixel values crash with a DecompressionBombError).
   - Zoom on every hand and every face.
   - Zoom on anywhere that lettering could appear: signs, screens, packaging, paper, clothing.
   - Zoom on the busiest corner of the background.
   A defect you only find at native pixels is still a defect: the image will be seen full-screen
   on a phone.

Reject on any one of these:

**Defects:** extra, fused or missing fingers; odd teeth or eyes; limbs that don't connect; any
pseudo-text or warped lettering in a generated image; straight lines that bend (door frames, shelves, tiles); objects
melting into each other; duplicated objects; impossible scale; inconsistent shadows; a watermark
or border.

**Slop tells:** waxy or airbrushed skin; HDR glow or halos; oversaturation; everything spotless
and symmetrical; a stock pose; a subject dead-centre for no reason; a plastic sheen on materials;
a background that dissolves into mush.

**Brand misses:** wrong place or culture; off-palette; contradicts what the business does; shows a
product, person or premises that could be mistaken for the real one; would look out of place next
to the site's own photos.

**Set misses:** two near-duplicates; one image graded differently from the rest; the set is all
people or all objects; fewer than 60% showcase slots; an offer from the brief that had proof but
no slot.

**Stranger test (showcase slots):** show the image alone to someone who has never seen the
business. Could they say what it sells? A laptop with a soft screen, hands on a notebook or a
calm office fails for a web agency. A real client site in a browser frame passes. A showcase slot
that fails is rejected, however good the photo is: move it to a mood slot if the mood quota has
room, otherwise remake it from proof.

**Capture misses (real pixels):** a cookie banner, chat bubble or consent wall that survived; a
half-loaded page (blank image boxes, a spinner, layout shift); lorem ipsum or placeholder copy;
someone's personal data (names, emails, phone numbers in a CRM or inbox screenshot) unless the
owner cleared it; a capture upscaled past 1.5x; a green fringe or a misaligned corner on a
`screen` composite (zoom on all four corners).

Then score what survives 1-5 on three questions:

- **Realism:** would a photographer believe it was shot?
- **Brand fit:** does it sit beside the site's own photos and the anchors without a seam?
- **Usefulness:** could a marketer drop it into a post today? For a showcase slot: does it pass
  the stranger test?

Ship only images that score 4+ on all three. Hold it to the anchors: an image that would look
cheap next to them is a 3. A reject gets one rewritten prompt that
names the failure ("hands out of frame", "light from a single window, no glow"), then a second
attempt with a different concept, then the slot falls back to the next-best harvested photo.
Never ship a known defect to make the count.
