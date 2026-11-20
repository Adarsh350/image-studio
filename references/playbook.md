# Playbook: placements, shot concepts by business type, and the default set

Use this to turn "N images for this business" into a shot list that a marketer would recognise as
the right set. `craft.md` decides how each image is made and judged. This file decides what to make.

## 1. Placements

| Placement | Deliver at | Ratio | Notes |
|---|---|---|---|
| Instagram / Facebook feed | 1080x1350 | 4:5 | The default feed shape. The profile grid now shows posts as 3:4, so keep the subject inside the centre 90% of the width. 3:4 at 1080x1440 avoids any grid crop, but some schedulers' publishing APIs stop at 4:5. |
| Carousel | 1080x1350 each | 4:5 | 3-5 frames from one shoot: wide, medium, detail. One grade across all frames. |
| Square post | 1080x1080 | 1:1 | Product and detail shots. Also the safe shape for a GBP cover (see below). |
| Story / Reel cover | 1080x1920 | 9:16 | Keep the top 250px and bottom 340px free of the subject: the UI covers them. |
| LinkedIn / Facebook feed | 1200x630 or 1080x1350 | 1.91:1 / 4:5 | Landscape for link posts, 4:5 for image posts. |
| Facebook cover | 1920x1080 | 16:9 | The subject sits in the centre 60%: mobile crops the sides. |
| LinkedIn company cover | 1920x1080 (crop to 1128x191 in the design tool) | 16:9 | Pick an image whose interest sits in a horizontal band; the strip is very thin. |
| Website hero / blog header | 1920x1080 | 16:9 | Clean negative space on one side for the headline. |
| Link preview (OG) | 1200x630 | 1.91:1 | Subject centred; reads at thumbnail size. |
| Meta / Google display ads | 1080x1080, 1080x1350, 1200x628, 1080x1920 | | Simple subject, one focal point, space for copy added in the design tool. |
| **Google Business Profile** | 1920x1080 cover, 1080x1080 others | 16:9 / 1:1 | **Real photos only. See below.** |

### Google Business Profile: real photos only

Google's photo policy for Business Profiles prohibits stock imagery, and photos have to represent
the business as it really is. Third-party guides report that AI-made and heavily edited images are
being rejected more often. Google hasn't confirmed this.

So **a GBP slot is always `existing` or a light `edit` of a real site photo.** A light edit means
crop, straighten, or remove a temporary overlay. It never invents anything.

Google recommends 720x720 or larger, as JPG or PNG between 10KB and 5MB. Third parties disagree on
the cover: some say 16:9 (1080x608 or 1024x576), and at least one now says square. Deliver the cover
at 1920x1080 with the subject centred, so a square crop still works.

The GBP gallery categories:

- cover
- exterior: three shots, at different times of day
- interior: three shots
- at work: three shots
- team: real people only
- products: real only
- common areas, rooms, and food & drink, depending on the business

If the site has no real photo for a category, **don't generate one.** List it in the reply under
"shoot these yourself", with a one-line brief per shot.

## 2. What makes a marketing image work

These patterns hold across the accounts and listings that perform. They come from documented
platform and creator guidance, not scraped metrics.

- **One subject, readable at thumbnail size.** If the point of the image isn't clear at 200px
  wide, it fails in the feed.
- **Real moments over posed ones.** Hands doing the work, the product in use, a customer mid-laugh
  and not looking at the lens.
- **Place is the brand.** The specific street, light, materials and people of where the business
  operates. Generic interiors are anonymous.
- **Detail shots carry quality.** Texture, craft and close-ups of the thing being made or done.
  They are also the easiest shots to generate convincingly.
- **Consistency beats novelty.** One grade, one light quality and one palette across the set, so
  the grid reads as one brand.
- **Room for copy.** About a third of the set needs clean negative space for a headline, and it
  should be planned, not cropped in later.
- **People who look like the customers.** Real ages and real builds, from the culture of the
  market the business sells to.

## 3. Shot concepts by business type

Each concept is a scene a real photographer would book. Mark which ones the site can supply. Never
generate the rows in **Real only** (see the Hard rules in SKILL.md). Generate the others only when
the site has nothing usable.

Every worked prompt below passes `codex_image.py --lint`. Adapt the place, the people and the
palette from the brief; never copy a prompt blind.

These 12 groups carry the worked prompts. The industry's own shot concepts, house style and slop
tells live in `industries/INDEX.md` (52 industries); read that section first and use the closest
group here for prompt shape.

### Clinic / dental / medical
Concepts:
- a clinician's gloved hands arranging instruments on a tray
- a calm treatment room in morning light, no patient
- a consultation across a desk, shot over the patient's shoulder
- a close-up of a hand holding a model of teeth or a spine
- a reception plant and seating detail
- a patient's relaxed hands in their lap
- sterilisation pouches stacked
- the clinician washing their hands at the sink

**Real only:** named doctors, the clinic exterior and signage, before-and-after photos.

> Editorial photograph, 50mm lens at f/2.8. A dentist's gloved hands lay out a mirror, probe and cotton rolls on a steel tray, mid-motion. A small modern clinic room with pale oak cabinetry and a sage-green wall. Soft late-morning daylight from a window on the left, gentle shadows to the right. Close-up from a slightly high angle, tray on the lower two-thirds, clean wall in the upper third. Muted, true-to-life colour.

### Real estate / property
Concepts:
- golden-hour facade detail: a balcony rail and planting
- living room with the light falling across the floor
- kitchen island with fruit and a cutting board
- a key and folder on a marble counter
- a view from a window looking out on the neighbourhood
- a couple measuring a wall, seen from behind
- a pool edge at dusk
- a neighbourhood street-life detail

**Real only:** the listed property itself, agents, the development's renders.

> Architectural interior photograph, 24mm lens, level verticals. A bright apartment living room with a linen sofa, an oak coffee table holding two ceramic cups and an open book, a woven rug. Low late-afternoon sun from tall windows on the right, long shadows across a pale stone floor. Wide shot at chest height, windows on the right third, empty wall upper left. Warm neutral tones with a muted olive cushion.

### Restaurant / cafe / bakery
Concepts:
- a barista pouring milk, close on the hands
- a chef plating, with steam
- a dish shot top-down on a worn table
- bread being torn
- a friends' table mid-meal, hands reaching in
- the bar counter detail
- the morning prep station
- a takeaway cup on a window ledge in street light

**Real only:** signature dishes as sold (generate a dish only as a mood or detail shot, never as
"our X"), the interior and exterior, the menu.

> Documentary food photograph, 35mm lens at f/2. A baker's floured hands tear open a crusty sourdough loaf above a scarred wooden counter, crumbs falling. A small bakery kitchen with a steel bench, a linen-lined proofing basket and a stack of paper bags behind. Soft daylight from a window behind and left, rim light on the crust. Tight medium close-up, loaf at the centre-right, dark counter space on the left. Warm, true-to-life colour.

### Home services (plumbing, HVAC, electrical, cleaning, landscaping)
Concepts:
- a technician reading a gauge on a rooftop AC unit
- hands tightening a fitting under a sink, with a work light
- a van door open with organised tools (no logo)
- an electrician testing a panel with a meter
- a freshly mown lawn edge
- a cleaner wiping a kitchen counter in morning light
- boots and a tool bag at a front door
- a homeowner handing over a cold drink (both people seen side-on)

**Real only:** the team, branded vans and uniforms, before-and-after photos of real jobs.

> Editorial photograph, 35mm lens at f/4. An HVAC technician in a grey work shirt crouches beside a rooftop air-conditioning unit, reading a pressure gauge on a hose, face in profile. A flat concrete roof with ducting and a low parapet; city rooftops soft in the background. Low warm sun just before dusk from the left, long shadows. Medium shot at eye level, technician on the left third, open sky across the upper half. Muted, true-to-life colour.

### Salon / barber / spa
Concepts:
- scissors mid-cut, close on the hair
- a barber's straight-razor line-up, side-on
- a towel stack and stone bowl
- hands applying a treatment
- the mirror station detail with tools
- a client's relaxed profile under a towel
- a nail-polish rack seen at a slant
- steam in a treatment room

**Real only:** named stylists, the premises, before-and-after photos.

> Editorial photograph, 85mm lens at f/2.2. A barber's hand guides a straight razor along a client's neckline, the client's head turned away, short dark hair. A narrow barbershop with a worn leather chair, a steel tray of combs and a fogged mirror behind. Warm tungsten lamp from above right, soft window fill from the left. Tight close-up from the side, razor and hand at the centre-left, dark wall on the right. Rich, natural skin tones.

### Gym / fitness / yoga / studio
Concepts:
- chalked hands gripping a bar
- a coach spotting a squat, seen from the side
- a yoga mat row in morning light with no people, or one person mid-pose
- a kettlebell row on a rubber floor
- a towel and water bottle on a bench
- a runner tying shoes
- a class mid-movement, motion slightly blurred
- a sweat-detail portrait, eyes down

**Real only:** named trainers, the gym's interior and branded kit.

> Documentary photograph, 35mm lens at f/2.8. Chalk-dusted hands of a woman in her forties grip a loaded barbell at the start of a deadlift, knuckles tight, forearms tense. A working gym with a black rubber floor, worn iron plates and a rack behind. Hard window light from the right across the bar, deep shadows on the floor. Low close-up, bar across the lower third, dark gym space above. Muted, gritty, true-to-life colour.

### Professional services (law, accounting, consulting, agency)
Concepts:
- two people reviewing printed documents with pens, hands only
- a whiteboard session seen from behind (no readable text)
- a coffee and notebook beside an open laptop with a dark screen
- a client meeting through a glass wall
- a hand signing a page
- a calm office corner at dusk
- a person on a phone by the window, side-on
- a team walking down a corridor, softly out of focus

**Real only:** partners and staff, the office, client logos, screenshots.

These concepts are **mood** slots. A professional-services set is mostly **showcase** (craft.md
section 2), and the showcase comes from proof, not from Codex:
- a client website the firm built, in a browser frame, or desktop and phone together (`mockup pair`)
- before and after of a site it rebuilt, from the Wayback Machine or supplied (`mockup split`)
- a dashboard, report or product UI it ships, captured or supplied (`mockup element` or `browser`)
- a demo element from its own site (a chat widget, a calculator, a score) on the brand ground
- a metric from the site, word for word, with clean ground left so it can be set as type later
- a generated laptop or phone scene with the real capture composited on its screen (`screen`)

> Editorial photograph, 50mm lens at f/2.8. Two colleagues' hands rest on printed pages spread across a walnut meeting table, one holding a pen to a margin note, a ceramic coffee cup and closed laptop beside them. A quiet meeting room with a linen curtain and a potted fig. Soft overcast daylight from a window on the left. Overhead three-quarter angle, papers in the lower half, clean table surface in the upper right. Muted warm neutrals, true-to-life colour.

### Hotel / hospitality / short-stay
Concepts:
- a made bed with the morning light across it
- a breakfast tray on the bed
- a balcony chair facing the view
- a bathroom detail: towels and a stone basin
- a key card on a dresser (no logo)
- a pool lounger with a towel
- a lobby seating corner
- luggage at the door

**Real only:** the actual rooms, pool, building and views (guests judge them against the real thing).

> Interior lifestyle photograph, 35mm lens at f/4. A breakfast tray with croissants, sliced mango, a glass of orange juice and a small coffee pot rests on rumpled white sheets, a folded newspaper with no visible print beside it. A hotel room with a cane headboard and sheer curtains. Soft early-morning sun through the sheers from the right, long gentle shadows. Top-down three-quarter angle, tray lower right, open sheet on the left. Warm, airy, true-to-life colour.

### Retail / boutique / e-commerce
Concepts:
- hands folding a garment on a counter
- a product on a natural surface in window light
- a rail of clothes seen at a slant
- paper wrapping and twine detail
- a customer holding an item up to the light, side-on
- a fitting-room curtain
- a shelf corner with styled objects
- a delivery box being opened

**Real only:** the products as sold (generated product images misrepresent what the customer gets),
the store.

> Editorial photograph, 50mm lens at f/2.8. A shop assistant's hands wrap a folded knit sweater in brown paper and twine on a worn oak counter, scissors and a roll of tissue beside it. A small boutique with plaster walls and a rail of garments softly behind. Soft window light from the left, gentle shadow to the right. Close-up from a slightly high angle, parcel at the centre-left, plain counter on the right. Muted earthy tones, true-to-life colour.

### Auto (dealer, garage, detailing)
Concepts:
- a mechanic's hands on an engine bay with a work lamp
- a detailer's foam wash, side-on
- tyre-tread detail
- a keys handover with hands only
- a workshop at dusk with the door half open
- a polishing pad mid-pass on paint
- a tools wall
- a steering wheel and dashboard in morning light (no logo)

**Real only:** the stock vehicles, the dealership, branded signage.

> Documentary photograph, 35mm lens at f/2.8. A mechanic's grease-marked hands tighten a bolt in an engine bay with a ratchet, a work lamp clipped to the bonnet. A busy workshop with a tool chest and a lifted car softly behind. Cool overhead fluorescent light mixed with the warm work lamp from the left. Close-up from above the wing, hands at the centre, dark engine detail around them. Gritty, true-to-life colour.

### Education / tutoring / training
Concepts:
- a student's hand writing in a notebook
- a tutor and student at a table, seen from behind
- a stack of books and a pencil case
- a hands-on lab or workshop moment
- a raised hand in a small class, soft focus
- a library corner in afternoon light
- a laptop and a sheet of handwritten notes (no readable text)
- a graduation-cap detail

**Real only:** named teachers, the campus, real students (minors especially: never generate
recognisable children for a real school).

> Editorial photograph, 50mm lens at f/2.8. A teenage student's hand writes in a spiral notebook with a pencil, a worn eraser and a highlighter beside it, the page's marks too soft to read. A wooden study table by a window with a stack of paperback books. Warm afternoon daylight from the right, soft shadows across the page. Close-up from a high angle, notebook in the lower two-thirds, table space in the upper left. Natural, true-to-life colour.

### Construction / trades / manufacturing
Concepts:
- a welder's sparks with a mask on, side-on
- a site at sunrise with a crane silhouette
- hands measuring timber
- a hard hat on a stack of plans (no readable text)
- a concrete pour detail
- a carpenter planing a board, shavings curling
- a safety-boot step on a scaffold
- a finished-joinery detail

**Real only:** the company's projects, the team, plant with branding.

> Documentary photograph, 35mm lens at f/4. A carpenter in a canvas apron planes the edge of an oak board on a workbench, pale shavings curling off the blade, forearms dusty. A timber workshop with clamps on the wall and stacked boards behind. Low morning sun through a high window on the left, dust visible in the light. Medium close-up at bench height, hands and plane on the right third, darker workshop on the left. Warm, true-to-life colour.

## 4. The default set ("N images for marketing")

When the user gives a count and no use, build the set from this mix. Scale it to N, rounding so it
sums exactly. The table sets **sizes**; craft.md section 2 sets **content**: whatever the sizes,
at least 60% of the rows are showcase slots, and every offer in the brief gets one when N allows.
Assign the showcase slots first, each to the size its proof fits best (a desktop capture suits a
landscape or a feed `pair`, a mobile capture a story, a UI element a square), then fill the rest
with mood slots.

| Share | Slot | Size | Preferred source |
|---|---|---|---|
| 30% | Feed posts: the work itself, or people-at-work, detail and place | 1080x1350 | proof / capture / mockup, else existing, else generate |
| 10% | Carousel trio from one shoot or one project (wide, medium, detail) | 1080x1350 | one project's captures, or multi-crop of one big site photo, else generate |
| 15% | Square: product, craft or UI detail | 1080x1080 | mockup element / existing, else generate |
| 15% | Story / Reel covers with negative space up top | 1080x1920 | mockup phone / existing crop, else generate |
| 15% | Web/social landscape with headline space | 1920x1080 | mockup browser or pair / screen / existing, else generate |
| 5% | OG / ad landscape | 1200x630 | mockup / existing |
| 10% | GBP: cover plus exterior/interior/at-work | 1920x1080 / 1080x1080 | **existing only**; if none, swap to a feed slot and list the GBP shots under "shoot these yourself" |

A worked example for N=20:

- 6 feed posts
- 2 carousel frames, plus 1 more from the same shoot
- 3 squares
- 3 stories
- 3 landscapes
- 1 OG
- 1 GBP cover, plus 1 GBP interior if the site has one

That comes to 21, so drop 1 feed post to land on 20.

**Multi-crop:** one large site photo (long side 3000px or more) often holds two or three
deliverables at the natural subject points: the wide scene, a person, and a detail on a table. Each
crop counts as a separate image only when it shows a different subject and its own crop needs an
upscale of 1.5x or less. `qa.py` flags crops that are too alike.
