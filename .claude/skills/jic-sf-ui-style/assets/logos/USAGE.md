# Logos: what each file is and how it may be used

All logos are SVGs, rendered as vectors at paint time (`Widgets.Svg_Image_Cls`). They are never rasterised and
scaled, never recoloured, distorted, cropped, outlined or shadowed, and never placed on a busy image. Keep at least
28 px of clear space round each logo in the funding band, which is free of motif squares and other marks. Copied from
AnyScan's `App/assets/` on 2026-10-23.

| File | What it is | Where it goes | Rules |
|---|---|---|---|
| `jic-smart-factory.svg` | JIC Smart Factory, horizontal lockup, the purple `#640ABA`, viewBox 848.6 × 134.76 | The header, right of the product lockup after a 34 px grey-lilac rule, 26 px tall beside a 54 px lockup (scaled with it) | The purple version is for white grounds. Its J-I-C bars are grid-fitted at DPR 1 (`mark_right` 452). It is the attribution: keep it in every JIC SF application's header. Do not use it as the product's own logo. |
| `edih-digimat-white.svg` | EDIH-DIGIMAT wordmark, solid white, **traced** (potrace from the official white PNG, IoU 0.996), not an official vector file | The funding band, first, 24 px tall | Only on the purple band (white on `#640ABA`). Replace it with the official vector when one is supplied. |
| `partner-ministry-white.svg` | Ministry of Industry and Trade of the Czech Republic, solid white, the lion without its field, **traced** (IoU 0.988) | The funding band, after the rule, 46 px | As Czech ministries show it on dark grounds. Only on the purple band. Replace it with the official vector when supplied. |
| `funder-eu-white.svg` | The EU emblem with "Funded by the European Union", solid white, **traced** (IoU 0.998) | The funding band, last, 46 px | At least as tall as the largest other logo (the EU's visibility rules). Its protection area (half the flag's height) stays free of any other element. Only on the purple band. When a band carries text, the EU disclaimer goes with it word for word (`Funding_Row_Cls.DISCLAIMER`; see `references/layout-components.md` § 9). |
| `anyscan-logo.svg` | AnyScan's full outlined logo (mark, wordmark and tagline), the purple, viewBox 609.8 × 140 | **Example only**, to show what a product lockup is | AnyScan's own logo. Never ship it in another product. |
| `anyscan-logo-wordmark.svg` | AnyScan's logo without its tagline, derived from `anyscan-logo.svg` | **Example only**: the example app's lockup, with the tagline as live text at origin (166.69, 128.0), size 24.55 units, `mark_right` 152, `thin_px` 0 | Replace it with the new product's own tagline-less logo and its own measured origin and size (`references/layout-components.md` § 2). |
| `anyscan-mark.svg` | AnyScan's mark alone, 140 × 140 | **Example only**: the empty image view's mark in the example app | Replace it with the new product's mark. |

The funding band's three logos are an obligation of the EDIH-DIGIMAT funding, not decoration. A project funded
otherwise shows its own funders' logos under its own rules, in the same band form (white on the purple, centred
group, rule, motif with clear space).
