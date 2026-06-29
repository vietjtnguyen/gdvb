# socketscope — backlog

Running list of ideas. Not commitments, not prioritized beyond rough grouping.
Check things off as they land.

## Done

- [x] Ship as a single standalone script (no Python packaging) with stdlib only
- [x] User-centric `README.md`
- [x] Clean up `--help` text (examples, grouped flags, type-id list)
- [x] A real name — **socketscope** (was `socket_graph.py`)
- [x] Better HTML `<title>`
- [x] "Download data (JSON)" button in the viewer
- [x] CLI JSON output (`--json`), `--no-html`, timestamped default base name
      (`socketscope-<ts>`), `-o -` to stdout, summary to stderr
- [x] `render` subcommand: rebuild HTML from a saved snapshot JSON without
      polling the system (stdin/file in, stdout/`-o` out)
- [x] Layered styling: baked **domain-agnostic** base (structure only) + per-type
      colors generated from `types[]` (single source for legend + node fill, can't
      drift) + per-snapshot `style` carrying the domain rules (listen/tree/io,
      prepopulated by captures) + viewer-owned interaction states
- [x] `render` works for **any directed graph** — only `nodes`+`edges` required;
      `types`/`meta`/`style` optional, labels fall back to `id` (so the viewer
      renders a plain tree/DAG JSON, not just socketscope captures)
- [x] Default type visibility is data-driven (`"hidden": true` per `types[]` entry,
      not hardcoded); the "Edge style" key text comes from a top-level `edge_key`
- [x] Generalize "Trace chain": generic **Select** tools (All/None/Invert/Grow/
      Shrink/Walk/Component) hardcoded in the viewer, plus data-driven **Traverse**
      tools (`traversals` block, endpoint-aware Cytoscape-selector rules + dir +
      flood/step). Trace chain is now the default traversal tool emitted to the JSON.
- [x] Unify selection focus (selected nodes + their incident edges un-faded, rest
      faded; nothing selected = nothing faded) and make edges non-selectable.
- [x] Data-driven **Force structure** modes (renamed from "Focus"): `force_structures`
      block, each emphasizes an edge selector; spring weighting unified to one
      per-edge weight; built-in `spread` + `distance from selected`. This was the last
      domain-coupled viewer feature — the viewer is now fully generic over the JSON.
- [x] **`dirtree` subcommand** — a second, non-socket model generator that walks a
      directory tree (nodes = files/dirs/symlinks, edges = containment + distinct
      symlink→target edges) into the same generic model, proving the viewer is
      domain-agnostic. CLI restructured into `sockets`/`dirtree`/`render`; bare
      invocation still defaults to `sockets`. Carries dirtree-specific `style`
      (exec files, dashed symlinks), traversals (Descendants / Path to root), and a
      `directory skeleton` force structure, plus per-node `size`/`mtime`/`ctime`/
      `user`/`group`/`perms`/`exec` metadata. Passing `-` reads a newline-separated
      path list from stdin (ancestors synthesized to connect them), so filtering —
      gitignore, etc. — is delegated to the upstream tool (`git ls-files | … dirtree -`)
      rather than reimplemented here.
- [x] Start this backlog

## Collector / data

- [ ] Link UNIX-domain socket **peers** via `ss -xp` (two ends of a UNIX pair —
      `/proc/net/unix` alone can't connect them). Optional, only if `ss` exists.
- [ ] Optionally cross-check counts against `ss`/`lsof` when present.
- [ ] Collapse the **same-path connected-UNIX "accept storm"** (e.g. the D-Bus
      system bus spawns hundreds of identical connected endpoints) into a single
      node with a count, or group them under their listener.
- [ ] **Network-namespace awareness**: note which netns was captured; optionally
      enumerate/visit other netns.
- [ ] **Container grouping**: label/group processes by cgroup/container.
- [ ] Listening **backlog / queue depths** and more socket detail in tooltips.
- [ ] IPv6 link-local **scope id** handling.
- [ ] **Big-endian** support: `/proc/net` addresses are host byte order, decoded
      assuming little-endian. Detect host endianness (e.g. `sys.byteorder`) and
      handle big-endian (s390x) so IP text is correct there too.

## Viewer / UX

- [ ] **Visualization layers** — a first-class JSON concept alongside `style` /
      `traversals` / `force_structures` that activates data→appearance mappings:
      e.g. map a numeric node field to a colormap (`size` → fill, `mtime` → heat),
      or scale node size by a metric, toggleable from a viewer control. dirtree
      already emits the numeric fields (`size`, `mtime`, `ctime`) such a layer
      would consume; sockets could expose connection/socket counts the same way.
- [ ] **jq-style query box** over the embedded JSON objects — a power-user
      complement to the substring/regex search (the natural next step now that
      the data is already one clean JSON model in the page).
- [ ] **Traversal-tool polish** (framework now exists; expose in UI):
  - [ ] surface `mode:step` + `deselectSource` (walk) + `recenter` as per-tool UI
        toggles / a "Traverse settings" row (currently data-only)
  - [ ] hop-limit / depth knob (generalize `step` to N hops)
  - [ ] seed inward from a remote (already expressible: a rule with `dir:"in"`)
  - [ ] **export the current selection / traced set** (JSON/CSV)
  - [ ] simple in-viewer editor to add/tweak a traversal rule live
- [ ] Search results **navigation** (next/prev, center on a match).
- [ ] **Keyboard shortcuts** (`/` focus search, `esc` clear, `f` fit, …).
- [ ] **Per-type counts** in the legend.
- [ ] Export the current view as **PNG/SVG**.
- [ ] **Persist UI state** (filters, pins, node positions) across re-runs
      (localStorage and/or encode in the file).
- [ ] **Node sizing** encodes a metric (socket count, connection count).
- [ ] **Diff two snapshots** to highlight what changed since last capture.
- [ ] Optional dark mode (note: the current light theme is an intentional design
      choice — only if there's demand).

## Sharing / packaging

- [x] Pick a **license** (MIT) and add `LICENSE`.
- [x] Add a **"Similar Projects/Tools"** section to the README (positioning vs.
      Weave Scope, EtherApe, bandwhich/nethogs, Hubble/Pixie, etc.).
- [ ] Keep the comparison **current** — recheck periodically; notable opening:
      Weave Scope is unmaintained since ~2021, so there's room for a modern,
      agentless single-host take. Watch new entrants (e.g. grigio/network-monitor, 2025).
- [ ] Add a **screenshot / short GIF** to the README.
- [ ] **Redaction mode**: scrub cmdline args / IP addresses before emitting, for
      safely sharing the HTML.
- [ ] Easy install story (download URL / release); shebang + `chmod +x` already work.
- [ ] `CHANGELOG.md` + version string.
- [ ] **Document the JSON schema** (`SCHEMA.md`): the generic typed-directed-graph
      format — `{meta, types, style, nodes, edges}`, the `<prefix>:<id>` convention,
      `cls`/`dir`/`listen`, and the `style` stylesheet — so it can be reused/produced
      by other tools.

## Quality / engineering

- [ ] **Tests** for the `/proc` parsers (fixture-based) + minimal CI.
- [ ] **Harden JSON-supplied `style`** for untrusted snapshots: strip/deny external
      references (`background-image: url(http…)`, web fonts) so `render` can't be
      coerced into a network fetch, preserving the offline guarantee.
- [ ] **Performance**: replace the O(N²) repulsion with a Barnes-Hut/quadtree
      approximation for very large hosts; cap/warn on huge graphs.
