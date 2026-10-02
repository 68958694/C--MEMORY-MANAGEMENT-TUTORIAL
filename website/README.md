# Growth & Beyond: premium website redesign

A single-page redesign of [growthandbeyond.in](https://growthandbeyond.in/), a career counselling, study abroad and Indian admissions practice in Royapettah, Chennai.

Plain HTML, CSS and JavaScript. No build step, no frameworks, no third-party requests: fonts are self-hosted.

## Structure

```
website/
├── index.html          # all content and sections
├── css/styles.css      # design system + layout (tokens at the top)
├── js/main.js          # menu, scroll reveals, counters, WhatsApp form
└── assets/
    ├── favicon.svg
    ├── apple-touch-icon.png
    ├── og-image.png    # preview shown when the link is shared on WhatsApp / social
    └── fonts/          # Fraunces + Manrope (SIL Open Font License)
```

## Preview locally

```bash
cd website
npx http-server -p 8080    # or: python3 -m http.server 8080
```

Open http://localhost:8080.

## Deploy

Upload the contents of `website/` to the web root of the hosting (for example `public_html/` in cPanel) so `index.html` is served at `https://growthandbeyond.in/`. It also works as-is on Netlify, Vercel, Cloudflare Pages or GitHub Pages.

The current site runs on WordPress. If the client wants to keep editing in WordPress, this design can serve as the reference for an Elementor rebuild instead.

## Sections

Hero · Services marquee · About + ratings (91% trust, 96% professionalism, 80% career clarity) · Services · Why choose us · How it works · Study abroad (10 destinations, Bachelors/Masters/Doctoral picker, 8-step journey) · Indian admissions + careers of tomorrow · Know your counsellor · Vision & mission · Call to action · FAQ · Contact · Footer

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
- [ ] **Logo.** The gold arrow mark is a stand-in. If the client has a logo, replace the `logo-mark` symbol in `index.html` and `assets/favicon.svg`.
- [ ] **Student count.** The old site shows "100+ students" in its counter but says "thousands of students" in the counsellor bio. This page uses 100+. Confirm the right figure.
- [ ] **Testimonials.** None are included, since the old site had no actual reviews to reuse. Send real Google reviews or client quotes and a section can be added.
- [ ] **Certifications.** The old site shows certificate images. Share them to add a credentials strip.
