# Growth & Beyond: premium website redesign

A single-page redesign of [growthandbeyond.in](https://growthandbeyond.in/), a career counselling, study abroad and Indian admissions practice in Royapettah, Chennai.

Plain HTML, CSS and JavaScript with no frameworks and no third-party requests (fonts are self-hosted). The colours, typeface and imagery follow the logo: navy blue, growth green and sky blue, with the graduation cap, globe and growth arrow.

The hero is a 3D scene built with three.js: a dotted globe, a 3D graduation cap and the green growth arrow (the logo in 3D), with study-abroad routes flying out of Chennai. It reacts to the mouse and to scrolling, pauses when off screen, and falls back to a static graphic when WebGL or motion is unavailable.

## Structure

```
website/
├── index.html          # all content and sections
├── css/styles.css      # design system + layout (tokens at the top)
├── js/main.js          # menu, scroll reveals, counters, 3D card tilt, WhatsApp form
├── js/hero-globe.js    # 3D hero (built file, do not edit by hand)
├── js/src/             # 3D hero source + world land mask
├── package.json        # only used to rebuild the 3D hero
├── tools/build-embeds.py  # builds the single-file and WordPress versions into dist/
└── assets/
    ├── favicon.svg
    ├── apple-touch-icon.png
    ├── og-image.jpg    # preview shown when the link is shared on WhatsApp / social
    └── fonts/          # Poppins + Manrope (SIL Open Font License)
```

## Preview locally

```bash
cd website
npx http-server -p 8080    # or: python3 -m http.server 8080
```

Open http://localhost:8080.

## Changing the 3D hero

Edit `js/src/hero-globe.js`, then rebuild the bundled file:

```bash
cd website
npm install
npm run build:globe
```

Destinations, colours and the route timing are at the top of the source file.

## Deploy

Upload the contents of `website/` (everything except `node_modules/`, `js/src/` and `package.json`, which are only for rebuilding) to the web root of the hosting (for example `public_html/` in cPanel) so `index.html` is served at `https://growthandbeyond.in/`. It also works as-is on Netlify, Vercel, Cloudflare Pages or GitHub Pages.

### On the existing WordPress site (no hosting access needed)

`python3 tools/build-embeds.py` writes two single-file builds to `dist/`:

- `Growth-and-Beyond-Website.html`: the whole site in one file, for previews (double-click to open).
- `homepage-for-wordpress.html`: a paste-in block. Every style is scoped under `#gb-site`, so the theme and Elementor kit styles can't override it, and it stretches to full width inside a boxed container.

To install it: in WordPress create a page, open it in Elementor, set **Page Layout → Elementor Canvas**, add an **HTML** widget and paste in `homepage-for-wordpress.html`. Publish, then set it as the homepage under **Settings → Reading**. The old homepage is untouched, so switching back is one setting. Clear any cache plugin afterwards, and exclude the page from "delay/combine JavaScript" if the globe doesn't appear.

## Sections

3D hero · Services marquee · About + ratings (91% trust, 96% professionalism, 80% career clarity) · Services · Why choose us · How it works · Study abroad (10 destinations, Bachelors/Masters/Doctoral picker, 8-step journey) · Indian admissions + careers of tomorrow · Know your counsellor · Vision & mission · Call to action · FAQ · Contact · Footer

## Where links go

| Button | Destination |
| --- | --- |
| Book a Pre-Counselling | Microsoft Forms pre-counselling form |
| Book an appointment | Edumilestones counsellor booking page |
| Start profiling / destinations / Career assessment | Edumilestones student profiler |
| Student dashboard | Edumilestones student dashboard |
| Campus / Online India admissions | Edumilestones college and online-programme search |
| Contact form, WhatsApp buttons | `wa.me/918438677808` with the enquiry pre-filled |
| Blog, Terms, Refunds | Existing pages on growthandbeyond.in |

The WhatsApp number lives in `SITE.whatsapp` at the top of `js/main.js` and in the `wa.me` links in `index.html`.

## Before going live

- [ ] **Counsellor photo.** Save a professional portrait as `assets/counsellor.jpg` and swap the `WB` placeholder (see the `✎ REPLACE` comment in the counsellor section).
- [ ] **Counsellor name and title.** "Waheedha Begum, Career Counsellor" is taken from the booking link. Confirm the exact name and title.
- [ ] **Original logo file.** The logo on the site is a vector redraw made from a photo of the screen. Ask for the original (SVG or a large transparent PNG) and replace the `logo-mark` symbol in `index.html` and `assets/favicon.svg`.
- [ ] **Student count.** The old site shows "100+ students" in its counter but says "thousands of students" in the counsellor bio. This page uses 100+. Confirm the right figure.
- [ ] **Testimonials.** None are included, since the old site had no actual reviews to reuse. Send real Google reviews or client quotes and a section can be added.
- [ ] **Certifications.** The old site shows certificate images. Share them to add a credentials strip.
