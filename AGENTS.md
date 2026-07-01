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

Not every script is a generator: **`scrub-model`** is a *filter* (reads a model JSON on
stdin, writes a scrubbed model to stdout). It's intentionally **not** named `*-graph` —
`just bundle-all` globs `*-graph` and would try to bundle it as a generator. Filters are
verb-noun (like `render-graph-html.py`); generators are `{subject}-graph`.

**`lsp-graph`** is the other odd one out: a shared LSP-protocol *client*, not a generator
you'd run directly (see README → *"LSP client vs. server orchestration"*). It takes
`--connect <unix-socket-path>` and never spawns a server — LSP specifies the message
protocol, not a transport or how to launch a server with the right project-specific
flags, so lsp-graph stays server-agnostic by not touching either. `clangd-lsp-graph` /
`pyright-lsp-graph` are the actual generators: each spawns its server over stdio,
bridges that to a fresh Unix domain socket, and runs `lsp-graph --connect` pointed at
it, streaming its JSON straight through **via a pipe read into `sys.stdout.write`, not
`stdout=None`/inherit** — inherit would hand the child process the real OS file
descriptor directly, bypassing a bundle's `contextlib.redirect_stdout` capture
entirely; a bundle also needs `main()` to `return` on success rather than always
`sys.exit(rc)`, since any `SystemExit` is read as an early/error exit that skips
rendering. Get both right and they bundle and render correctly (`just bundle
clangd-lsp-graph` produces a working `dist/clangd-lsp-graph-scope`) — verified by
actually running the bundled output, not just reasoning about it. They still aren't
fully self-contained the way other bundles are, though: the bundled artifact needs a
separate `lsp-graph` reachable at runtime (`PATH`, or copied alongside in `dist/`),
since they orchestrate it as its own process rather than importing it. Adding a new
language/server means a new small wrapper script in this same shape; `lsp-graph`
itself shouldn't need to change.

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
