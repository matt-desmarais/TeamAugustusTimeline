#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime
from pathlib import Path

from PIL import Image  # pip install Pillow

IMAGES_DIR = Path("images")
THUMBS_DIR = IMAGES_DIR / "thumbs"
FONTS_DIR = Path("fonts")   # optional: host fonts locally here
OUTPUT_HTML = Path("timeline.html")

THUMB_MAX_SIZE = (800, 800)
JPEG_QUALITY = 80


# ---------------- Helpers ----------------

def humanize_title(slug: str) -> str:
    if not slug:
        return "Untitled"
    text = re.sub(r"[-_]+", " ", slug).strip()
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), text)


def parse_date_from_filename(filename: str):
    """
    Parse date from the filename.
    Tries (in order):
      1) YYYY-MM-DD or YYYY_MM_DD at the start
      2) DD-MM-YYYY-...
      3) MM-YYYY-...
      4) YYYY-...
      5) Any 4-digit year (19xx or 20xx) anywhere in the name
    Returns (date_obj, label, rest_slug)
    """
    name = os.path.splitext(filename)[0]

    m = re.match(r"^(\d{4})[-_](\d{1,2})[-_](\d{1,2})(?:[-_](.*))?$", name)
    if m:
        yyyy, mm, dd, rest = m.groups()
        try:
            dt = datetime(int(yyyy), int(mm), int(dd))
        except ValueError:
            dt = None
        label = f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        return dt, label, (rest or "")

    m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})(?:[-_](.*))?$", name)
    if m:
        dd, mm, yyyy, rest = m.groups()
        try:
            dt = datetime(int(yyyy), int(mm), int(dd))
        except ValueError:
            dt = None
        label = f"{dd.zfill(2)}-{mm.zfill(2)}-{yyyy}"
        return dt, label, (rest or "")

    m = re.match(r"^(\d{1,2})-(\d{4})(?:[-_](.*))?$", name)
    if m:
        mm, yyyy, rest = m.groups()
        try:
            dt = datetime(int(yyyy), int(mm), 1)
        except ValueError:
            dt = None
        label = f"{mm.zfill(2)}-{yyyy}"
        return dt, label, (rest or "")

    m = re.match(r"^(\d{4})(?:[-_](.*))?$", name)
    if m:
        yyyy, rest = m.groups()
        try:
            dt = datetime(int(yyyy), 1, 1)
        except ValueError:
            dt = None
        label = f"{yyyy}"
        return dt, label, (rest or "")

    m = re.search(r"(19|20)\d{2}", name)
    if m:
        yyyy = int(m.group(0))
        try:
            dt = datetime(yyyy, 1, 1)
        except ValueError:
            dt = None
        label = str(yyyy)
        rest = name.replace(str(yyyy), "")
        rest = re.sub(r"^[-_]+|[-_]+$", "", rest)
        return dt, label, rest

    return None, name, ""


def ensure_thumbnail(src_path: Path) -> Path:
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    thumb_path = THUMBS_DIR / src_path.name

    if thumb_path.exists():
        return thumb_path

    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            im.thumbnail(THUMB_MAX_SIZE)
            save_kwargs = {"optimize": True}
            if thumb_path.suffix.lower() in {".jpg", ".jpeg"}:
                save_kwargs["quality"] = JPEG_QUALITY
            im.save(thumb_path, **save_kwargs)
    except Exception as e:
        print(f"[WARN] could not create thumbnail for {src_path}: {e}")
        try:
            import shutil
            shutil.copy2(src_path, thumb_path)
        except Exception as e2:
            print(f"[WARN] and could not copy original either: {e2}")

    return thumb_path


def collect_events():
    if not IMAGES_DIR.is_dir():
        raise SystemExit(f"Images directory not found: {IMAGES_DIR}")

    events = []
    for entry in sorted(IMAGES_DIR.iterdir()):
        if not entry.is_file():
            continue

        ext = entry.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            continue

        dt, label, rest_slug = parse_date_from_filename(entry.name)

        full_rel_path = f"{IMAGES_DIR.name}/{entry.name}"

        thumb_path = ensure_thumbnail(entry)
        thumb_rel_path = f"{IMAGES_DIR.name}/{THUMBS_DIR.name}/{thumb_path.name}"

        base_no_ext = os.path.splitext(entry.name)[0]
        title = humanize_title(rest_slug or entry.stem)

        year = dt.year if dt else None
        if year is None:
            m = re.search(r"(19|20)\d{2}", label)
            if m:
                year = int(m.group(0))
            else:
                m2 = re.search(r"(19|20)\d{2}", base_no_ext)
                if m2:
                    year = int(m2.group(0))

        txt_path = IMAGES_DIR / (base_no_ext + ".txt")
        text_content = ""
        if txt_path.exists():
            text_content = txt_path.read_text(encoding="utf-8", errors="ignore")

        jxl_path = IMAGES_DIR / (base_no_ext + ".jxl")
        jxl_rel_path = f"{IMAGES_DIR.name}/{base_no_ext}.jxl" if jxl_path.exists() else None

        events.append({
            "image": thumb_rel_path,
            "full_image": full_rel_path,
            "jxl_image": jxl_rel_path,
            "date_label": label,
            "file_label": base_no_ext,
            "title": title,
            "description": "",
            "text": text_content,
            "year": year,
            "sort_key": dt.isoformat() if dt else None,
        })

    events.sort(key=lambda ev: (ev["sort_key"] is None, ev["sort_key"] or ""))
    for ev in events:
        ev.pop("sort_key", None)
    return events


# ---------------- Font support (optional) ----------------

def font_face_css_if_present() -> str:
    """
    If you place these files in ./fonts/, the generator will emit @font-face rules.
      - fonts/AtkinsonHyperlegible-Regular.woff2
      - fonts/Lexend-Regular.woff2
      - fonts/OpenDyslexic-Regular.woff2
    You can name them differently if you adjust the mapping below.
    """
    mappings = [
        ("Atkinson Hyperlegible", "AtkinsonHyperlegible-Regular.woff2"),
        ("Lexend", "Lexend-Regular.woff2"),
        ("OpenDyslexic", "OpenDyslexic-Regular.woff2"),
    ]

    lines = []
    for family, filename in mappings:
        path = FONTS_DIR / filename
        if path.exists():
            # note: keep it simple, regular weight only
            lines.append(
                f"""@font-face {{
  font-family: "{family}";
  src: url("{FONTS_DIR.name}/{filename}") format("woff2");
  font-display: swap;
}}"""
            )

    return "\n".join(lines)


# ---------------- HTML ----------------

def build_html(events):
    events_json = json.dumps(events, ensure_ascii=False, indent=2)
    font_face_css = font_face_css_if_present()

    html_template = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>OSS Jedburghs: Team Augustus</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />

<!-- Open Graph (Facebook, LinkedIn, etc.) -->
<meta property="og:title" content="OSS Jedburghs: Team Augustus — Timeline & Records">
<meta property="og:description" content="Discover the history, reports, and archival main pages of OSS Jedburghs Team Augustus.">
<meta property="og:image" content="https://teamaugust.us/ossmedal.png">
<meta property="og:url" content="https://teamaugust.us/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Team Augustus">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="OSS Jedburghs: Team Augustus">
<meta name="twitter:description" content="Explore operational history and archival records of OSS Jedburghs Team Augustus.">
<meta name="twitter:image" content="https://teamaugust.us/ossmedal.png">

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FEDSBJB4CZ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-FEDSBJB4CZ');
</script>

  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { scroll-behavior: smooth; }

    /* Optional locally-hosted fonts (only emitted if files exist in ./fonts/) */
__FONT_FACE_CSS__

    :root{
      --a11y-font-scale: 1;

      /* theme variables */
      --a11y-bg: #151311;
      --a11y-fg: #f4f0e4;
      --a11y-card-bg: #f4ecd5;
      --a11y-card-fg: #3c2d1b;

      /* font variables */
      --a11y-font-body: "Georgia", "Times New Roman", serif;
      --a11y-font-ui: "Courier New", monospace;

      /* image inversion */
      --invert-images: 0;
    }

    html { font-size: calc(16px * var(--a11y-font-scale)); }

    body{
      font-family: var(--a11y-font-body);
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.08), transparent 55%),
        radial-gradient(circle at bottom right, rgba(0,0,0,0.5), var(--a11y-bg) 80%);
      color: var(--a11y-fg);
      padding: 2rem 1rem;
      display: flex;
      justify-content: center;
    }

    /* MUTUALLY EXCLUSIVE visual modes */
    body.theme-dark{
      --a11y-bg: #151311;
      --a11y-fg: #f4f0e4;
      --a11y-card-bg: #f4ecd5;
      --a11y-card-fg: #3c2d1b;
    }

    body.theme-light{
      --a11y-bg: #f7f2e2;
      --a11y-fg: #1c140c;
      --a11y-card-bg: #fffaf0;
      --a11y-card-fg: #1c140c;
    }

    body.high-contrast{
      --a11y-bg: #000;
      --a11y-fg: #fff;
      --a11y-card-bg: #000;
      --a11y-card-fg: #fff;
    }

    :focus-visible{ outline: 3px solid #ffd35a; outline-offset: 3px; }

    .page{ width: 100%; max-width: 960px; }

    h1{
      text-align: center;
      margin-bottom: 0.25rem;
      font-size: 2rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--a11y-fg);
    }

    .subtitle{
      text-align: center;
      font-size: 0.85rem;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      opacity: 0.85;
      margin-bottom: 1.0rem;
      font-family: var(--a11y-font-ui);
    }

    /* Accessibility bar */
    .a11y-bar{
      display:flex;
      flex-wrap: wrap;
      align-items:center;
      justify-content:center;
      gap: 0.6rem;
      margin: 0.8rem 0 1.2rem;
      padding: 0.6rem 0.7rem;
      border-radius: 999px;
      border: 1px solid rgba(80, 70, 55, 0.9);
      background: radial-gradient(circle at top left, rgba(255,255,255,0.10), rgba(0,0,0,0.65));
      box-shadow: 0 10px 20px rgba(0,0,0,0.45), inset 0 0 0 1px rgba(255,255,255,0.18);
      font-family: var(--a11y-font-ui);
    }

    .a11y-btn{
      border-radius: 999px;
      border: 1px solid rgba(32, 25, 16, 0.9);
      padding: 0.35rem 0.9rem;
      background: radial-gradient(circle at 15% 10%, #f9f1dc, #d3c4a0);
      color: #3c2d1b;
      cursor: pointer;
      letter-spacing: 0.10em;
      text-transform: uppercase;
      font-size: 0.78rem;
      font-family: var(--a11y-font-ui);
      white-space: nowrap;
    }

    .a11y-btn[aria-pressed="true"]{
      box-shadow: inset 0 0 0 2px rgba(0,0,0,0.35);
    }

    .a11y-btn:disabled{
      opacity: 0.45;
      cursor: not-allowed;
      filter: grayscale(0.6);
    }

    .a11y-select{
      border-radius: 999px;
      border: 1px solid rgba(32, 25, 16, 0.9);
      padding: 0.35rem 0.8rem;
      background: #f9f1dc;
      color: #3c2d1b;
      font-size: 0.78rem;
      font-family: var(--a11y-font-ui);
    }


/* Keep the accessibility controls anchored and usable as text scales */
.a11y-bar{
  position: sticky;
  top: 0.75rem;
  z-index: 1000;

  /* keep it centered and stable */
  margin: 0.8rem auto 1.2rem;
  max-width: 960px;
  width: 100%;

  /* allow wrapping instead of expanding offscreen */
  flex-wrap: wrap;
  justify-content: center;

  /* lock the control sizing so it doesn't balloon with global font scaling */
  font-size: clamp(12px, 1.2vw, 14px);
  line-height: 1.2;

  /* avoid layout "jump" when it becomes sticky */
  backdrop-filter: blur(4px);
}

/* Make controls size consistent regardless of page font scaling */
.a11y-btn,
.a11y-select{
  font-size: 1em;          /* relative to .a11y-bar font-size (locked above) */
  line-height: 1.2;
  padding: 0.45em 0.95em;  /* scales with toolbar only */
}

/* Prevent long labels from causing toolbar overflow */
.a11y-btn{
  max-width: 100%;
  white-space: nowrap;
}

/* If screen is narrow, keep it tidy */
@media (max-width: 520px){
  .a11y-bar{
    gap: 0.45rem;
    top: 0.5rem;
    padding: 0.55rem 0.55rem;
  }
  .a11y-btn, .a11y-select{
    padding: 0.42em 0.75em;
  }
}



    /* Site nav */
    .site-nav{
      display: flex;
      justify-content: center;
      gap: 2.5rem;
      margin-bottom: 1.5rem;
      font-family: var(--a11y-font-ui);
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 2.25rem;
      flex-wrap: wrap;
    }

    .site-nav a{
      color: var(--a11y-fg);
      text-decoration: none;
      padding: 0.2rem 1.2rem;
      border-bottom: 1px solid transparent;
      opacity: 0.85;
      transition: border-color 0.12s ease-out, opacity 0.12s ease-out;
    }
    .site-nav a:hover{ border-color: var(--a11y-fg); opacity: 1; }
    .site-nav a.active{ border-color: var(--a11y-fg); opacity: 1; }

    /* Year nav */
    .timeline-nav-wrapper{
      display: flex;
      justify-content: center;
      width: 100%;
      margin-bottom: 1.75rem;
      padding: 0.6rem 0.7rem;
      border-radius: 999px;
      background: radial-gradient(circle at top left, rgba(255,255,255,0.09), rgba(0,0,0,0.7));
      border: 1px solid rgba(80, 70, 55, 0.9);
      box-shadow: 0 10px 20px rgba(0,0,0,0.65), inset 0 0 0 1px rgba(255,255,255,0.18);
      overflow: hidden;
      max-width: 100%;
      font-family: var(--a11y-font-ui);
    }

    .timeline-nav{
      display: flex;
      justify-content: center;
      align-items: center;
      flex-wrap: wrap;
      width: 100%;
      text-align: center;
      gap: 1.0rem 2.0rem;
      padding: 0.25rem 0.5rem 0.35rem;
    }

    .nav-pill{
      font-family: var(--a11y-font-ui);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      border-radius: 999px;
      border: 1px solid rgba(32, 25, 16, 0.9);
      padding: 0.35rem 1.0rem;
      background: radial-gradient(circle at 15% 10%, #f9f1dc, #d3c4a0);
      color: #3c2d1b;
      cursor: pointer;
      box-shadow: 0 1px 1px rgba(255,255,255,0.6), 0 2px 4px rgba(0,0,0,0.6);
      white-space: nowrap;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .nav-pill-disabled{ opacity: 0.35; pointer-events: none; filter: grayscale(0.6); }

    /* Timeline */
    .timeline{ margin: 2rem 0; padding-left: 0; }
    .timeline-year-group{ margin-bottom: 3rem; }

    .timeline-year-heading{
      font-family: var(--a11y-font-body);
      font-weight: bold;
      font-size: 2.0rem;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      text-align: center;
      margin-bottom: 1rem;
      color: var(--a11y-fg);
      opacity: 0.92;
    }

    .timeline-year-grid{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 2rem;
    }

    .timeline-item{ margin: 0; padding: 0; scroll-margin-top: 80px; }
    .timeline-item-full{ grid-column: 1 / -1; }
    .timeline-item-full .timeline-image-wrapper img{ max-width: 100%; }

    .timeline-card{
      background: var(--a11y-card-bg);
      background-image:
        linear-gradient(90deg, rgba(255,255,255,0.15) 0, transparent 30%, transparent 70%, rgba(0,0,0,0.04) 100%),
        repeating-linear-gradient(
          to bottom,
          rgba(0,0,0,0.04) 0px,
          rgba(0,0,0,0.04) 1px,
          transparent 1px,
          transparent 22px
        );
      border-radius: 0.5rem;
      padding: 0.9rem 1rem 1.2rem;
      border: 1px solid rgba(70, 60, 40, 0.9);
      box-shadow: 0 16px 26px rgba(0, 0, 0, 0.7), inset 0 0 0 1px rgba(255, 255, 255, 0.2);
      color: var(--a11y-card-fg);
      position: relative;
      height: 100%;
    }

    .back-to-top{
      position: absolute;
      top: 0.4rem;
      right: 0.4rem;
      font-family: var(--a11y-font-ui);
      font-size: 0.7rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      padding: 0.25rem 0.55rem;
      border-radius: 5px;
      border: 1px solid rgba(40, 32, 20, 0.8);
      background: linear-gradient(#faf3dd, #dfcfac);
      color: #3c2d1b;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .timeline-header{ display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.5rem; }

    .timeline-date{
      font-family: var(--a11y-font-ui);
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.2em;
      color: #5b4a32;
      padding: 0.15rem 0.55rem;
      border-radius: 999px;
      border: 1px solid rgba(60, 46, 30, 0.7);
      background: linear-gradient(#f9f1dc, #e3d4b2);
      align-self: flex-start;
    }

    .timeline-file{
      font-family: var(--a11y-font-ui);
      font-size: 0.8rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #7a6242;
      opacity: 0.9;
      word-break: break-all;
    }

    .timeline-image-wrapper{
      margin-top: 0.75rem;
      border-radius: 0.45rem;
      overflow: hidden;
      border: 1px solid rgba(60, 47, 30, 0.9);
      box-shadow: 0 3px 8px rgba(0,0,0,0.6), inset 0 0 18px rgba(0,0,0,0.25);
      filter: sepia(0.55) contrast(1.02) saturate(0.8);
      display: flex;
      justify-content: center;
      align-items: center;
    }

    /* invert images */
    .timeline-image-wrapper img,
    .fullscreen-overlay img{
      filter: invert(var(--invert-images));
    }

    .timeline-image-wrapper img{
      max-width: 90%;
      height: auto;
      margin: 0 auto;
      display: block;
      cursor: zoom-in;
    }


.timeline-textbox{
  margin: 1.1rem 0 0 0;

  /* USE THEME VARIABLES (works for dark/light/high-contrast) */
  background: var(--a11y-card-bg);
  color: var(--a11y-card-fg);

  border: 2px solid currentColor; /* strong border in high-contrast */
  padding: 1rem 1.2rem;
  border-radius: 0.45rem;

  width: 100%;
  box-sizing: border-box;

  text-align: center;
  font-family: var(--a11y-font-ui);
  font-size: 0.95rem;

  white-space: pre-wrap;
  overflow-wrap: break-word;

  max-height: none;
  overflow: visible;

  /* Remove low-contrast “paper” shading that fights high contrast */
  box-shadow: none;
}

.timeline-textbox a{
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}




    /* Fullscreen overlay */
    .fullscreen-overlay{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.92);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      cursor: zoom-out;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.35s ease-out;
    }
    .fullscreen-overlay.is-visible{ opacity: 1; pointer-events: auto; }
    .fullscreen-overlay img{
      max-width: 95vw;
      max-height: 95vh;
      box-shadow: 0 0 40px rgba(0,0,0,0.9);
      border-radius: 0.5rem;
    }

    .fullscreen-message{
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0,0,0,0.6);
      padding: 1.2rem 2rem;
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 8px;
      color: #f7f3e8;
      font-family: var(--a11y-font-ui);
      font-size: 1.2rem;
      text-align: center;
      max-width: 90%;
      box-shadow: 0 0 18px rgba(0,0,0,0.7);
      opacity: 1;
      transition: opacity 0.35s ease-out;
    }
    .fullscreen-message.hidden{ opacity: 0; pointer-events: none; }

    .page-footer{
      margin-top: 3rem;
      text-align: center;
      font-size: 0.75rem;
      opacity: 0.75;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-family: var(--a11y-font-ui);
    }

    @media (max-width: 640px){
      body{ padding: 1.25rem 0.75rem; }
      .site-nav{ gap: 1.2rem; font-size: 0.72rem; }
    }
  </style>
</head>

<body class="theme-dark">
  <div id="fullscreen-overlay" class="fullscreen-overlay" aria-modal="true" role="dialog">
    <div id="initial-message" class="fullscreen-message">
      This project is a work in progress<br><br>
      Click anywhere to continue
    </div>
    <picture id="fullscreen-picture">
      <source id="fullscreen-source-jxl" type="image/jxl">
      <img id="fullscreen-image" alt="Full-size archive image">
    </picture>
  </div>

  <main class="page" id="page-top">
    <h1>OSS Jedburghs: Team Augustus</h1>
    <p class="subtitle">Operational Timeline &amp; Archival Records</p>

    <div class="a11y-bar" role="region" aria-label="Accessibility controls">
      <button class="a11y-btn" id="a11y-text-dec" type="button" aria-label="Decrease text size">A-</button>
      <button class="a11y-btn" id="a11y-text-inc" type="button" aria-label="Increase text size">A+</button>

      <button class="a11y-btn" id="a11y-contrast" type="button" aria-pressed="false">
        High Contrast
      </button>

      <button class="a11y-btn" id="a11y-theme" type="button" aria-pressed="false">
        Dark / Light
      </button>

      <!-- IMPORTANT: "Font" removed from label per your request -->
      <select class="a11y-select" id="a11y-font" aria-label="Typeface">
        <option value="default">Default</option>
        <option value="atkinson">Atkinson</option>
        <option value="arial">Arial</option>
        <option value="tahoma">Tahoma</option>
        <option value="trebuchet">Trebuchet</option>
        <option value="times">Times</option>
        <option value="lexend">Lexend</option>
        <option value="opendyslexic">OpenDyslexic</option>
      </select>

      <button class="a11y-btn" id="a11y-invert" type="button" aria-pressed="false">
        Invert Images
      </button>
    </div>

    <nav class="site-nav" aria-label="Site pages">
      <a href="about.html">About</a>
      <a href="reports.html">Reports</a>
      <a href="roger.html">Roger</a>
      <a href="sources.html">Sources</a>
    </nav>

    <div class="timeline-nav-wrapper" aria-label="Year navigation">
      <div id="timeline-nav" class="timeline-nav"></div>
    </div>

    <div id="timeline" class="timeline"></div>

    <p class="page-footer">Office Of Strategic Services &mdash; Declassified Reproduction</p>
  </main>

  <script>
    const events = __EVENTS_JSON__;

    const yearLoadState = {};
    let fullscreenOverlay = null;
    let fullscreenImage = null;

    function openFullscreen(src, alt, jxlSrc = null) {
      if (!fullscreenOverlay || !fullscreenImage) return;
      const source = document.getElementById("fullscreen-source-jxl");
      if (source) source.srcset = jxlSrc ? jxlSrc : "";
      fullscreenImage.src = src;
      fullscreenImage.alt = alt || "Full-size archive image";
      fullscreenOverlay.classList.add("is-visible");
    }

    function closeFullscreen() {
      if (!fullscreenOverlay || !fullscreenImage) return;
      const msg = document.getElementById("initial-message");
      if (msg) msg.classList.add("hidden");
      fullscreenOverlay.classList.remove("is-visible");
      setTimeout(() => {
        if (!fullscreenOverlay.classList.contains("is-visible")) {
          const source = document.getElementById("fullscreen-source-jxl");
          if (source) source.srcset = "";
          fullscreenImage.src = "";
        }
      }, 350);
    }

    function showIntroOverlay() {
      if (!events || events.length === 0) return;
      const first = events[0];
      const src = first.full_image || first.image;
      const jxl = first.jxl_image || null;
      const msg = document.getElementById("initial-message");
      if (msg) msg.classList.remove("hidden");
      openFullscreen(src, first.title || first.file_label || "Archive photo", jxl);
    }

    function markYearImageLoaded(yearStr) {
      const state = yearLoadState[yearStr];
      if (!state) return;
      state.loaded += 1;
      if (!state.ready && state.loaded >= state.total) {
        state.ready = true;
        const btn = document.querySelector('.nav-pill[data-year="' + yearStr + '"]');
        if (btn) btn.classList.remove("nav-pill-disabled");
      }
    }

    function renderTimeline(events) {
      const container = document.getElementById("timeline");
      container.innerHTML = "";
      Object.keys(yearLoadState).forEach((k) => delete yearLoadState[k]);

      const yearMap = new Map();
      const UNKNOWN_KEY = "Unknown";

      events.forEach((item, index) => {
        const key = (item.year != null) ? String(item.year) : UNKNOWN_KEY;
        if (!yearMap.has(key)) yearMap.set(key, []);
        yearMap.get(key).push({ item, index });
      });

      const numericYears = Array.from(yearMap.keys())
        .filter((k) => k !== UNKNOWN_KEY)
        .map((k) => parseInt(k, 10))
        .sort((a, b) => a - b)
        .map((n) => String(n));

      const hasUnknown = yearMap.has(UNKNOWN_KEY);

      numericYears.forEach((yearStr) => {
        const entries = yearMap.get(yearStr) || [];
        yearLoadState[yearStr] = { total: entries.length, loaded: 0, ready: false };
      });

      numericYears.forEach((yearStr) => {
        const groupEl = document.createElement("section");
        groupEl.className = "timeline-year-group";
        groupEl.id = yearStr;

        const heading = document.createElement("h2");
        heading.className = "timeline-year-heading";
        heading.textContent = yearStr;
        groupEl.appendChild(heading);

        const gridEl = document.createElement("div");
        gridEl.className = "timeline-year-grid";

        const entries = yearMap.get(yearStr) || [];
        entries.forEach(({ item, index }) => {
          const itemEl = document.createElement("article");
          itemEl.className = "timeline-item";
          itemEl.dataset.eventIndex = index.toString();
          itemEl.dataset.year = yearStr;

          if (item.text && item.text.trim().length > 0) itemEl.classList.add("timeline-item-full");

          const cardEl = document.createElement("div");
          cardEl.className = "timeline-card";

          const topLink = document.createElement("a");
          topLink.className = "back-to-top";
          topLink.textContent = "Top";
          topLink.href = "#page-top";
          cardEl.appendChild(topLink);

          const headerEl = document.createElement("div");
          headerEl.className = "timeline-header";

          const dateEl = document.createElement("span");
          dateEl.className = "timeline-date";
          dateEl.textContent = item.date_label || "";
          headerEl.appendChild(dateEl);

          if (item.file_label) {
            const fileEl = document.createElement("span");
            fileEl.className = "timeline-file";
            fileEl.textContent = item.file_label;
            headerEl.appendChild(fileEl);
          }

          cardEl.appendChild(headerEl);

          const imgWrapper = document.createElement("div");
          imgWrapper.className = "timeline-image-wrapper";

          const picture = document.createElement("picture");
          const img = document.createElement("img");
          img.src = item.image;  // thumbnail
          img.alt = item.title || "Archive photo";
          img.decoding = "async";

          img.addEventListener("load", () => markYearImageLoaded(yearStr));
          img.addEventListener("error", () => markYearImageLoaded(yearStr));

          img.addEventListener("click", () => {
            const fullSrc = item.full_image || item.image;
            const jxlSrc = item.jxl_image || null;
            openFullscreen(fullSrc, item.title || item.file_label || "Archive photo", jxlSrc);
          });

          picture.appendChild(img);
          imgWrapper.appendChild(picture);
          cardEl.appendChild(imgWrapper);

          if (item.text && item.text.trim().length > 0) {
            const textBox = document.createElement("div");
            textBox.className = "timeline-textbox";
            textBox.textContent = item.text;
            cardEl.appendChild(textBox);
          }

          itemEl.appendChild(cardEl);
          gridEl.appendChild(itemEl);
        });

        groupEl.appendChild(gridEl);
        container.appendChild(groupEl);
      });

      if (hasUnknown) {
        const entries = yearMap.get(UNKNOWN_KEY) || [];
        if (entries.length > 0) {
          const groupEl = document.createElement("section");
          groupEl.className = "timeline-year-group";

          const heading = document.createElement("h2");
          heading.className = "timeline-year-heading";
          heading.textContent = "Unknown Date";
          groupEl.appendChild(heading);

          const gridEl = document.createElement("div");
          gridEl.className = "timeline-year-grid";

          entries.forEach(({ item, index }) => {
            const itemEl = document.createElement("article");
            itemEl.className = "timeline-item";
            itemEl.dataset.eventIndex = index.toString();
            if (item.text && item.text.trim().length > 0) itemEl.classList.add("timeline-item-full");

            const cardEl = document.createElement("div");
            cardEl.className = "timeline-card";

            const topLink = document.createElement("a");
            topLink.className = "back-to-top";
            topLink.textContent = "Top";
            topLink.href = "#page-top";
            cardEl.appendChild(topLink);

            const headerEl = document.createElement("div");
            headerEl.className = "timeline-header";

            const dateEl = document.createElement("span");
            dateEl.className = "timeline-date";
            dateEl.textContent = item.date_label || "";
            headerEl.appendChild(dateEl);

            if (item.file_label) {
              const fileEl = document.createElement("span");
              fileEl.className = "timeline-file";
              fileEl.textContent = item.file_label;
              headerEl.appendChild(fileEl);
            }

            cardEl.appendChild(headerEl);

            const imgWrapper = document.createElement("div");
            imgWrapper.className = "timeline-image-wrapper";

            const picture = document.createElement("picture");
            const img = document.createElement("img");
            img.src = item.image;
            img.alt = item.title || "Archive photo";
            img.decoding = "async";

            img.addEventListener("click", () => {
              const fullSrc = item.full_image || item.image;
              const jxlSrc = item.jxl_image || null;
              openFullscreen(fullSrc, item.title || item.file_label || "Archive photo", jxlSrc);
            });

            picture.appendChild(img);
            imgWrapper.appendChild(picture);
            cardEl.appendChild(imgWrapper);

            if (item.text && item.text.trim().length > 0) {
              const textBox = document.createElement("div");
              textBox.className = "timeline-textbox";
              textBox.textContent = item.text;
              cardEl.appendChild(textBox);
            }

            itemEl.appendChild(cardEl);
            gridEl.appendChild(itemEl);
          });

          groupEl.appendChild(gridEl);
          container.appendChild(groupEl);
        }
      }
    }

    function renderTimelineNav(events) {
      const nav = document.getElementById("timeline-nav");
      nav.innerHTML = "";

      const yearSet = new Set();
      events.forEach((item) => { if (item.year != null) yearSet.add(item.year); });
      const years = Array.from(yearSet).map(Number).sort((a, b) => a - b);

      years.forEach((year) => {
        const yearStr = String(year);
        const link = document.createElement("a");
        link.className = "nav-pill nav-pill-disabled";
        link.textContent = yearStr;
        link.href = "#" + yearStr;
        link.dataset.year = yearStr;
        nav.appendChild(link);
      });
    }

    // ---------- Accessibility settings ----------
    function applyA11ySettings(settings) {
      const scale = Math.min(1.8, Math.max(0.85, settings.scale || 1));
      document.documentElement.style.setProperty("--a11y-font-scale", String(scale));

      // Mutually-exclusive theme modes
      document.body.classList.remove("theme-dark", "theme-light", "high-contrast");
      if (settings.contrast) {
        document.body.classList.add("high-contrast");
      } else {
        document.body.classList.add(settings.light ? "theme-light" : "theme-dark");
      }

      // Invert images (independent)
      document.documentElement.style.setProperty("--invert-images", settings.invert_images ? "1" : "0");

      // Typeface (some require local font files to actually load)
      const setFont = (stack) => {
        document.documentElement.style.setProperty("--a11y-font-body", stack);
        document.documentElement.style.setProperty("--a11y-font-ui", stack);
      };

      const mode = settings.font || "default";
      if (mode === "atkinson") {
        setFont('"Atkinson Hyperlegible", Arial, sans-serif');
      } else if (mode === "arial") {
        setFont('Arial, Helvetica, sans-serif');
      } else if (mode === "tahoma") {
        setFont('Tahoma, Arial, sans-serif');
      } else if (mode === "trebuchet") {
        setFont('"Trebuchet MS", Arial, sans-serif');
      } else if (mode === "times") {
        setFont('"Times New Roman", Times, serif');
      } else if (mode === "lexend") {
        setFont('"Lexend", Arial, sans-serif');
      } else if (mode === "opendyslexic") {
        setFont('"OpenDyslexic", Arial, sans-serif');
      } else {
        // Default split
        document.documentElement.style.setProperty("--a11y-font-body", '"Georgia", "Times New Roman", serif');
        document.documentElement.style.setProperty("--a11y-font-ui", '"Courier New", monospace');
      }

      // UI state
      const contrastBtn = document.getElementById("a11y-contrast");
      const themeBtn = document.getElementById("a11y-theme");
      const invertBtn = document.getElementById("a11y-invert");
      const fontSelect = document.getElementById("a11y-font");

      if (contrastBtn) contrastBtn.setAttribute("aria-pressed", settings.contrast ? "true" : "false");
      if (themeBtn) themeBtn.setAttribute("aria-pressed", settings.light ? "true" : "false");
      if (invertBtn) invertBtn.setAttribute("aria-pressed", settings.invert_images ? "true" : "false");

      if (fontSelect) fontSelect.value = mode;

      // Lock theme toggle while in high contrast (prevents fighting states)
      if (themeBtn) themeBtn.disabled = !!settings.contrast;
    }

    function loadA11ySettings() {
      try {
        const raw = localStorage.getItem("a11y_settings");
        if (!raw) return { scale: 1, light: false, contrast: false, font: "default", invert_images: false };
        const parsed = JSON.parse(raw);
        return Object.assign({ scale: 1, light: false, contrast: false, font: "default", invert_images: false }, parsed);
      } catch {
        return { scale: 1, light: false, contrast: false, font: "default", invert_images: false };
      }
    }

    function saveA11ySettings(settings) {
      try { localStorage.setItem("a11y_settings", JSON.stringify(settings)); } catch {}
    }

    document.addEventListener("DOMContentLoaded", () => {
      fullscreenOverlay = document.getElementById("fullscreen-overlay");
      fullscreenImage = document.getElementById("fullscreen-image");

      if (fullscreenOverlay) fullscreenOverlay.addEventListener("click", () => closeFullscreen());
      document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeFullscreen(); });

      let a11y = loadA11ySettings();
      applyA11ySettings(a11y);

      const incBtn = document.getElementById("a11y-text-inc");
      const decBtn = document.getElementById("a11y-text-dec");
      const contrastBtn = document.getElementById("a11y-contrast");
      const themeBtn = document.getElementById("a11y-theme");
      const fontSelect = document.getElementById("a11y-font");
      const invertBtn = document.getElementById("a11y-invert");

      if (incBtn) incBtn.addEventListener("click", () => {
        a11y.scale = Math.min(1.8, (a11y.scale || 1) + 0.1);
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      if (decBtn) decBtn.addEventListener("click", () => {
        a11y.scale = Math.max(0.85, (a11y.scale || 1) - 0.1);
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      if (contrastBtn) contrastBtn.addEventListener("click", () => {
        a11y.contrast = !a11y.contrast;
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      if (themeBtn) themeBtn.addEventListener("click", () => {
        if (a11y.contrast) return; // locked while high contrast is on
        a11y.light = !a11y.light;
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      if (fontSelect) fontSelect.addEventListener("change", () => {
        a11y.font = fontSelect.value;
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      if (invertBtn) invertBtn.addEventListener("click", () => {
        a11y.invert_images = !a11y.invert_images;
        applyA11ySettings(a11y); saveA11ySettings(a11y);
      });

      renderTimeline(events);
      renderTimelineNav(events);

      if (events.length > 0) showIntroOverlay();
    });
  </script>
</body>
</html>
"""
    html = html_template.replace("__EVENTS_JSON__", events_json)
    html = html.replace("__FONT_FACE_CSS__", font_face_css if font_face_css.strip() else "/* (no local fonts found in ./fonts/) */")
    return html


def main():
    events = collect_events()
    html = build_html(events)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated {OUTPUT_HTML} with {len(events)} events.")
    print(f"Thumbnails in: {THUMBS_DIR}")
    print("Optional fonts: put .woff2 files in ./fonts/ (see script comments)")

if __name__ == "__main__":
    main()
