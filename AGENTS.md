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
