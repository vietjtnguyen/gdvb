# AGENTS.md

Guidance for AI agents (and humans) working in this repo. **The conventions live in
[README.md](README.md)** — read these sections before adding or renaming scripts:

- **Naming** (README → *Bundling → Naming*): the scripts are Python but named like
  POSIX programs — lowercase kebab-case, no `.py` extension. Generators are
  `{subject}-graph` (e.g. `sockets-graph`); their bundles are `{subject}-graph-scope`
  in `dist/`; the viewer is `render-graph-html.py`.
- **Generator conventions** (README → *Bundling → Generator conventions*): the C1–C4
  contract every generator must satisfy — a top-level `main()` that writes the model
  JSON to stdout and returns on success; `-o`/`--out` reserved; no top-level `Viewer`;
  errors via `SystemExit`. `just bundle` lints these and refuses violations.

Common tasks: `just bundle <generator>` (or `just bundle-all`) to build a single-file
bundle into `dist/`; `just format` to run `black`.

## Testing viewer JS changes without a browser

There's no browser/headless-DOM test harness in this repo, and you don't need one for
most changes. Two cheap Node-based checks catch the errors that actually happen when
editing `render-graph-html.py`'s embedded `<script>` (especially via `sed`/scripted
transforms rather than hand edits):

1. **Syntax check.** Render any generator through the viewer, regex-extract the last
   `<script>...</script>` block from the output HTML, write it to a temp `.js` file, and
   run `node --check` on it:
   ```bash
   ./sockets-graph | ./render-graph-html.py > /tmp/v.html
   python3 -c "
   import re
   html = open('/tmp/v.html').read()
   open('/tmp/app.js','w').write(re.findall(r'<script>(.*?)</script>', html, re.S)[-1])
   "
   node --check /tmp/app.js
   ```
   This catches broken braces/parens from a botched transform before they'd only ever
   surface as a silent blank page in a real browser.

2. **Logic verification against real data (no DOM at all).** The viewer's selection/
   traversal/visibility functions (`runTraversal`, `visBy`, `nodeVisible`, etc.) are pure
   functions over plain data structures (`INC`, `ECLS`, `NCLS`) derived from the JSON
   model — they don't touch Cytoscape or the DOM. So you can copy just those functions
   into a standalone `node -e` script, rebuild their inputs from a real generator's JSON
   output (not synthetic fixtures), and call them directly to check behavior — e.g.
   confirming a new traversal rule walks exactly the hops you intend:
   ```bash
   ./dirtree-graph --max-depth 4 . > /tmp/m.json
   node -e '
   const m = require("/tmp/m.json");
   // ...rebuild INC/ECLS from m.nodes/m.edges, paste in the function under test,
   // call it with a real seed id from m.nodes, and inspect the result.
   '
   ```
   This is only possible because the viewer is architected data-first (see "the model is
   the seam" in README) — the algorithms are decoupled from rendering, so they're testable
   without ever constructing a DOM, shadow or otherwise.

Both are cheap enough to run after every embedded-JS edit; do this before claiming a
viewer change works, since `black`/`python -m py_compile` only cover the Python side.
