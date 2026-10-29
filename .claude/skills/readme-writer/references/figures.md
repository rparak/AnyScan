# README figures

## Generated, never drawn

- **One deterministic script** writes every README image from repository data (results files,
  configuration, models). Same inputs, same images: fixed seeds, a fixed renderer backend
  (matplotlib `Agg`), pinned plotting library versions, no timestamps in the image.
- The script has a `--out` option, so it can be run into a temporary directory and compared with
  the committed images; a test may compare the graphs byte for byte.
- Images are never edited by hand, cropped in an image editor or exported from a notebook.
- A render of a 3-D model shows the model the project actually uses for its results (for example the
  simplified model a computation runs on, not a nicer illustration), and the caption says which.

How a figure is generated, themed, saved and made deterministic, and the default look without a brand,
are project-style-rpx `references/figures.md`. This page decides what a README figure shows and how it is presented.

## Light and dark

Every chart, graph or diagram exists in a light and a dark version, shown with `<picture>`:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="Media/result_dark.png">
  <img src="Media/result_light.png" alt="What the image shows, in at least twelve words, including the key values" width="85%">
</picture>
```

- The `<img>` is the light fallback and carries `alt` and an explicit `width` (a percentage keeps
  it readable on narrow screens).
- The dark version is drawn for a dark background (text, axes and grid light), not inverted.
- **A render or photograph of a scene** (a 3-D view, a camera image, an animated preview) may exist
  in one version when it is legible on both backgrounds: it carries its own background. The project
  reference lists which images are single-version.
- A brand mark in the header and an author's avatar are not figures: they need no caption, listed with
  their reason in `references/check_readme.json` (`uncaptioned_figures`); their alt text still has
  at least 12 words.

## Content

- **No title inside the image**: the README caption carries it.
- Keep what the reader needs to read it: axes with units, a legend, data labels on the values the
  text quotes, status labels on variants, footnotes for estimates ("simulation estimate — X not
  modelled").
- Meaning never by colour alone, and the same thing in the same colour in every figure (the
  palette and its contrast rules: project-style-rpx `references/figures.md`).
- Readable at README width (about 830 px on GitHub): font sizes at least about 10 pt at the
  rendered size; no more than about 6 series in one graph.

## Captions and alt text

- A numbered caption directly below each figure: `**Figure N:** what it shows. How to read it.`
  (in an HTML table cell: `<p><b>Figure N:</b> ...</p>`). Figures are numbered in document order,
  including those inside `<details>`.
- The caption states the source and the nature of the numbers (estimate, measurement, date).
- Alt text of at least 12 words describing the content and its key values, not the file name and
  not "a figure".

## How many, how large

- **3-4 figures in the visible part**: the key figure at the top and one or two results figures.
  The rest go into a collapsible gallery (`<details>`) under Results.
- **Size budget**: default at most 400 KB per image and 6 MB for all images shown (`check_readme.py`
  warns above it). A project that decides some media may be larger (an animated preview, a large
  render) records it in `references/check_readme.json`, each budget with its reason, instead of
  accepting warnings:
  ```json
  {"image_budgets": [{"glob": "Media/*.gif", "max_kb": 10240, "reason": "the cycle previews"}],
   "media_budget": {"max_mb": 30, "reason": "two previews and the renders"}}
  ```
  The first matching glob wins; a command-line `--max-image-kb` / `--max-media-mb` overrides the
  file. Reduce with the figure size and DPI, a limited palette, or a crop in the script, never by
  hand.
- **Animated previews (GIF)**: one palette for all frames (no flicker), no dithering, a few frames
  per second; to meet the budget use fewer colours first, then fewer frames. GIF frame delays come in
  10 ms steps, so an exact average frame rate needs alternating delays.
- **Videos are not in the repository.** The README shows a GIF preview; the full video is a release
  asset (uploaded only with the owner's approval), linked by its asset URL
  (`https://github.com/<owner>/<repo>/releases/download/<tag>/<file>`) beside the release page.
- PNG for renders and graphs; SVG only when it renders the same on GitHub in both themes.

## Before committing

**Look at every new or changed image**, light and dark, at README width: labels not clipped,
legend not covering data, the status labels and footnotes present, the dark version legible.
A passing test does not show a misplaced label.
