# The Log College & Seminary — program catalog site

A static website that presents all eleven LCS degree programs in full: requirements, every course, and every assigned lecture, reading, and paper, plus a searchable course catalog and resource library. It has no framework and no npm; Python 3 builds it.

## Structure

```
data/site.json            School info, links, and per-program metadata (summary, duration, PDF link)
data/programs/*.json      One file per program, transcribed from the official PDF guides (see data/SCHEMA.md)
src/assets/               CSS, JS, logo, icons
build.py                  Generator: reads data/, writes public/
public/                   The built site (what gets deployed)
netlify.toml              Netlify build settings
```

## Build and preview locally

```bash
python3 build.py
```

```bash
python3 -m http.server 4410 --directory public
```

Then open http://localhost:4410.

## Deploy to Netlify

Option A, drag and drop: run `python3 build.py`, then drop the `public/` folder on https://app.netlify.com/drop.

Option B, from a Git repository: push this folder to GitHub and import it in Netlify. `netlify.toml` publishes the committed `public/` folder, so run `python3 build.py` and commit before pushing.

## Updating content

- **A course changes:** edit that program's file in `data/programs/` (same shape as the others), then rebuild. A course shared by several programs appears once in the catalog if its content matches in every program file; if it differs, the course page shows each version.
- **A new program guide link or description:** edit `data/site.json`.
- The official PDF guides stay authoritative. Every program page links to its guide on Google Drive, and those PDFs carry the links to each lecture and text.
