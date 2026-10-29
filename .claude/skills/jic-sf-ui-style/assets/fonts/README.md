# Fonts

- `PublicSans-{Regular,Medium,SemiBold,Bold}.ttf` and `PublicSans-OFL.txt`: Public Sans, SIL Open Font License 1.1,
  the UI face. Ship the licence text with the fonts. The OFL allows bundling and redistribution, but not selling the
  fonts on their own or using the reserved font name for a modified version.
- `JetBrainsMono-{Regular,Medium,SemiBold,Bold}.ttf` and `JetBrainsMono-OFL.txt`: JetBrains Mono, SIL OFL 1.1, for
  machine values only.

They are static instances at exactly the four weights the UI requests (400, 500, 600, 700), copied from AnyScan's
`App/assets/fonts/`. AnyScan builds them reproducibly with `Example/UI/build_fonts.py` from google/fonts commit
`e1d6480102fed30739fead0faee463101f892c8f`, checking SHA-256 and instancing with fontTools. Do not replace them with
the variable fonts: Qt 5.15 synthesises every weight but the default.

**Never add GT America or GT Super Display here.** They are the brand guide's commercial faces and are never bundled.
See `references/typography.md`.
