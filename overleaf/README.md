# MAPO rebuttal: editable Overleaf project

Upload `mapo-rebuttal-overleaf.zip` using Overleaf's **New Project → Upload
Project**, then open `main.tex` and compile with **pdfLaTeX** (the default).

Edit one reviewer file at a time:

- `responses/EAwd.tex`
- `responses/zXPm.tex`
- `responses/kaLY.tex`
- `responses/TM2s.tex`

`main.tex` includes these four files in reviewer order. Each reviewer begins on
a new page. Tables, quotations, emphasis, and mathematical notation are ordinary
LaTeX, so this project needs no Markdown conversion step or shell escape in
Overleaf. All required packages are part of Overleaf's standard TeX installation.

The response wording and numerical values are unchanged from the Markdown
originals included in `markdown/`. Conversion changes only formatting and the
escaping required by LaTeX. `source-manifest.json` records the originals' hashes.
The reviewer labels in `main.tex` are document navigation, outside the responses.

Edit the `.tex` files directly in Overleaf. The Markdown files are reference
copies and do not automatically synchronize with subsequent LaTeX edits.
