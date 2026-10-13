# Chaos Console typography

Every page loads `shared/typography.css` after its room styles. Font assets are
served locally through `shared/fonts.css`; pages do not request Google Fonts.

| Role | Family | Weight | Reference |
| --- | --- | --- | --- |
| Large page titles | Bebas Neue | 400 | Binder cover |
| Editorial section and chapter headings | Barlow Condensed | 800 | Binder part headings |
| Reading text and explanations | Barlow | 400; 600 for emphasis | Possession callout and Binder introduction |
| Interface, compact headings, tables and charts | IBM Plex Sans | 400–700 | Eastern Front Studio |

Keep the Studio workspace in IBM Plex Sans, including its compact title and
reading panels. Real code samples retain the system monospace stack. Large
numeric displays use IBM Plex Sans with tabular figures.

Use the `--cc-font-display`, `--cc-font-heading`, `--cc-font-body`,
`--cc-font-ui`, and `--cc-font-code` tokens in new styles. Existing `--th-*`
and room tokens resolve to the same families. Do not add font-face aliases
that relabel one font as another or claim a static file supports every weight.

Room colors, content and responsive type sizes remain in the room stylesheets.
If adding a new editorial title class, include it in the editorial role in
`typography.css`; compact component headings default to the UI role.

Barlow, Barlow Condensed and Bebas Neue WOFF2 files come from the Google Fonts
distribution (fonts.gstatic.com). Their SIL Open Font License notices are in
`shared/threshold/fonts/`. IBM Plex Sans files and their license are in `fonts/`.
The typography update of October 13, 2026 uses the existing Barlow 400/600 and
Barlow Condensed 600 files, plus the corresponding additional real weights,
Barlow italics, and Bebas Neue 400.
