# AGENTS.md

Guidance for AI agents (and humans) working in this repo. **The conventions live in [README.md](README.md)** — read these sections before adding or renaming scripts:

- **Naming** (README → *Bundling → Naming*): lowercase kebab-case, no `.py` extension. Generators are `{subject}-graph`; the viewer is `gdvb-render`; `just bundle <generator>` writes `dist/gdvb-{subject}` (e.g. `gdvb-clangd-lsp-graph` → `dist/gdvb-clangd-lsp`). `gdvb-lsp-graph` matches that name shape but is actually a shared LSP client, not a generator — `gdvb-clangd-lsp-graph`/`gdvb-pyright-lsp-graph` are the ones that spawn a server and call it (README → *"LSP client vs. server orchestration"*).
- **Generator conventions** (README → *Bundling → Generator conventions*): C1–C4 — top-level `main()` writes model JSON to stdout and returns on success; `-o`/`--out` reserved; no top-level `Viewer`; errors via `SystemExit`. `just bundle` lints these.

`gdvb-scrub` is the one script that actually breaks the `*-graph` naming: it's a filter (stdin model JSON → stdout), not a generator, kept off the `-graph` suffix so `bundle-all`'s `*-graph` glob doesn't try to bundle it.

Common tasks: `just bundle <generator>` / `just bundle-all`; `just format` (black).

**Markdown files (this one, README.md, BACKLOG.md) soft-wrap: write each paragraph or list item as one line, however long, and let the editor/viewer wrap it for display.** Don't hard-wrap at a fixed column — a wrapped paragraph turns a one-sentence edit into a multi-line diff every time the text reflows.

## Testing viewer JS changes without a browser

No browser/DOM harness exists here, and you don't need one. Two cheap checks catch what actually breaks when editing `gdvb-render`'s embedded `<script>`:

1. **Syntax check** — render through the viewer, extract the last `<script>` block, run `node --check`:
   ```bash
   ./gdvb-sockets-graph | ./gdvb-render > /tmp/v.html
   python3 -c "import re; open('/tmp/app.js','w').write(re.findall(r'<script>(.*?)</script>', open('/tmp/v.html').read(), re.S)[-1])"
   node --check /tmp/app.js
   ```

2. **Logic check against real data, no DOM** — the viewer's selection/traversal/visibility functions (`runTraversal`, `visBy`, `nodeVisible`, ...) are pure functions over plain data (`INC`/`ECLS`/`NCLS` derived from the JSON model), so copy them into a `node -e` script, feed real generator output, and call them directly:
   ```bash
   ./gdvb-dirtree-graph --max-depth 4 . > /tmp/m.json
   node -e 'const m = require("/tmp/m.json"); /* rebuild INC/ECLS, paste fn, call it */'
   ```

Run both after any embedded-JS edit — `black`/`py_compile` only cover the Python side.
