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
- [x] **`dirtree-graph` generator** — a non-socket model generator that walks a
      directory tree (nodes = files/dirs/symlinks, edges = containment + distinct
      symlink→target edges) into the same generic model, proving the viewer is
      domain-agnostic. Carries dirtree-specific `style` (exec files, dashed symlinks),
      traversals (Descendants / Path to root), a `directory skeleton` force structure,
      and per-node `size`/`mtime`/`ctime`/`user`/`group`/`perms` metadata. Passing `-`
      reads a newline-separated path list from stdin (ancestors synthesized to connect
      them), so filtering — gitignore, etc. — is delegated to the upstream tool
      (`git ls-files | dirtree-graph -`). Originally a `dirtree` subcommand of
      render-graph-html.py; split out into a standalone script once the "model is the seam"
      architecture was established.
- [x] **`sockets-graph` generator + render-graph-html.py is now a pure viewer.** The socket
      `/proc` capture (the original flagship) was extracted out of render-graph-html.py into a
      standalone `sockets-graph` (filtering flags `--ignore*`, emits JSON to stdout),
      completing the split: **every generator is now standalone** (`sockets-graph`,
      `dirtree-graph`, `cmake-graph`) and **render-graph-html.py is just the renderer** —
      it reads a model (stdin/file) and writes the HTML viewer, with no domain code. The
      output plumbing (`resolve_outputs`/`write_outputs`, the `--json`/`--no-html` flags)
      went away with capture; generators emit JSON only and the viewer's `-o` writes HTML.
- [x] **Make the viewer truly field-generic.** It previously copied only a fixed
      allowlist (`id/label/full/type/listen`) into Cytoscape element data, so custom
      fields couldn't drive selectors — `listen` was hardcoded and dirtree's
      `node[exec="yes"]` rule silently never matched. Now every scalar node/edge field
      is spread into element data (booleans coerced to `yes`/`no`), so `style`/traversal
      selectors can key on anything a generator emits.
- [x] **Multi-class model.** Replaced singular `node.type` + ad-hoc edge `cls` with a
      CSS-style class model: nodes and edges each carry a `classes` array
      (multi-membership), catalogs renamed to `node_classes` / `edge_classes` (both with
      a color/legend/visibility entry per class). Styles compose across matching class
      rules (e.g. a file that's also `executable` gets the file fill + an executable
      border; a class with no `color` is a pure modifier). The viewer has two legends
      (node + edge) with **OR-visibility** (hidden only when all of an element's classes
      are off) and an `other` catch-all for uncataloged classes. Also de-socketed the
      tree-label toggle (triage #1) — hiding tree-edge labels is now just hiding the
      `tree` edge class. Breaking change; v0, no back-compat.
- [x] **`cmake-graph` generator** (standalone). Reads CMake's File API codemodel-v2
      from a configured build dir and emits the target/dependency/source graph as JSON,
      piped to `render` — the first generator that lives *outside* render-graph-html.py,
      validating the "model is the seam" architecture. Targets classed by type; `link`
      (target→dep) + `source` (target→file) edges; source nodes start hidden. A real
      dependency DAG, so Topo BFS + "Depended on by" shine.
- [x] **`lsp-graph` — LSP call-graph generator** (clangd-first, standalone). Drives a
      language server over stdio JSON-RPC (minimal `Content-Length` client), waits for the
      background index, resolves seeds (`--file` → a file's functions, `--seed NAME` →
      `workspace/symbol`), and walks `callHierarchy/incomingCalls` outward to `--depth`
      (capped by `--max-nodes`) into a caller→callee graph. Nodes classed by SymbolKind
      (function/method/constructor + a `seed` modifier border); Callers/Callees traversals
      + Topo BFS. **clangd 14 only implements incomingCalls** (callers / impact direction;
      outgoingCalls returns empty), and clangd starts indexing only after the first
      `didOpen` — both handled. Verified against `orchard/`.
      Future modes (still open): type-hierarchy + reference graphs; `--direction` once a
      server supports outgoingCalls; whole-project `--all`; other servers via `--server`.
- [x] **"Show all" / "Hide all" buttons** on each legend (node classes / edge
      classes) — bulk-set every class in that legend in one click instead of
      per-row toggling; single `applyVis()`/`reheat()` for the whole batch.
- [x] **Any/All visibility toggle** — a per-legend "Match: Any/All" button
      switches that legend's visibility logic between OR (any of an element's
      classes shown keeps it visible — the original/default) and AND (every
      one of its classes must be shown). Independent per legend (`nodeMatchAll`/
      `edgeMatchAll`), since node classes and edge classes have separate
      hide-sets (`visBy` takes the mode as a parameter).
- [x] **`dirtree-graph`: "Siblings" traversal** — a new `edge.sibling` class
      chains each directory's children together in label order (O(k) edges per
      directory of k children, not a full O(k²) pairwise mesh); flooding from
      any one child along that chain reaches every sibling without walking
      back up through the parent and down its whole subtree. Hidden by default
      (not a real filesystem relationship, would clutter the skeleton) - still
      traversal-selectable while hidden, since only node visibility gates the
      walk. Synthesized once in `_finalize` from the existing containment
      edges, shared by both the walk and stdin path-list builders.
- [x] **Generalized `just bundle <generator>`** — fuse the viewer + any generator into one
      self-contained runnable script in `dist/` (generate + render in a single invocation).
      Pure shell: cats `render-graph-html.py` (now entirely under `class Viewer`, so it
      contributes one top-level name) + the generator (catted last → its `main` is the sole
      one) + the `bundle_main.py` glue, then `black`. Formalized **generator conventions**
      (C1 main→JSON-on-stdout; C2 `-o`/`--out` reserved; C3 don't define `Viewer`; C4 errors
      via `SystemExit`) — documented in README and **linted by the recipe**. Replaces the
      one-off socket-only `sockets.py` bundle.
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
- [ ] **Multi-host merge**: run `sockets-graph` on several machines and combine
      the snapshots into one model, with remote TCP endpoints stitched together
      across hosts (the same conceptual peer, seen from both sides). Leaning
      toward a separate **stitching script** run post-merge (matching remote
      IP:port pairs across snapshots) over baking a hostname into node IDs at
      generation time — deconflicting the id namespace is only one small part
      of the actual stitching problem, so solve them together rather than
      pre-committing to an id scheme now.
- [ ] **`lsp-graph`: types as first-class nodes** — currently only functions/
      methods/constructors (SymbolKind restricted to the call-hierarchy kinds)
      are emitted; classes/structs/enums/etc. should appear as their own class
      of node (distinct from the `seed` modifier border), with edges for
      containment/usage, not just calls. Ties into clangd's `typeHierarchy/*`
      requests, separate from `callHierarchy/incomingCalls`.
- [ ] **`lsp-graph`: whole-project symbol enumeration** — a mode to seed from
      *every* first-class type/symbol in the project (e.g. `workspace/symbol`
      with an empty/wildcard query, or walking `textDocument/documentSymbol`
      across all indexed files) instead of requiring `--file`/`--seed` up
      front, so you can explore a codebase without already knowing a starting
      point. Distinct from the types-as-nodes item above — this is about seed
      *discovery*, not node *kind*.

## Viewer / UX

- [ ] **Choose BFS roots explicitly** — let **pinned** nodes force-seed as roots
      for Topo BFS (`topoBFS`'s in-degree-order seeding, `render-graph-html.py`
      `topoBFS()`), instead of always picking real in-degree-0 nodes first.
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
      model, so other tools can produce/consume it. This is *the* ecosystem seam
      (generators emit JSON and pipe to `render`; they don't import render-graph-html.py).
      Deferred until the model settles — the upcoming multi-class `node_classes`/
      `edge_classes` refactor will reshape it, so writing it now is premature (a first
      draft was removed for that reason).

## Quality / engineering

- [ ] **Tests** for the `/proc` parsers (fixture-based) + minimal CI.
- [ ] **Harden JSON-supplied `style`** for untrusted snapshots: strip/deny external
      references (`background-image: url(http…)`, web fonts) so `render` can't be
      coerced into a network fetch, preserving the offline guarantee.
- [ ] **Performance**: replace the O(N²) repulsion with a Barnes-Hut/quadtree
      approximation for very large hosts; cap/warn on huge graphs.
