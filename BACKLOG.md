# gdvb — backlog

Running list of ideas. Not commitments, not prioritized beyond rough grouping.
Check things off as they land.

## Done

- [x] Ship as a single standalone script (no Python packaging) with stdlib only
- [x] User-centric `README.md`
- [x] Clean up `--help` text (examples, grouped flags, type-id list)
- [x] A real name — **gdvb** (was `socket_graph.py`)
- [x] Better HTML `<title>`
- [x] "Download data (JSON)" button in the viewer
- [x] CLI JSON output (`--json`), `--no-html`, timestamped default base name
      (`gdvb-<ts>`), `-o -` to stdout, summary to stderr
- [x] `render` subcommand: rebuild HTML from a saved snapshot JSON without
      polling the system (stdin/file in, stdout/`-o` out)
- [x] Layered styling: baked **domain-agnostic** base (structure only) + per-type
      colors generated from `types[]` (single source for legend + node fill, can't
      drift) + per-snapshot `style` carrying the domain rules (listen/tree/io,
      prepopulated by captures) + viewer-owned interaction states
- [x] `render` works for **any directed graph** — only `nodes`+`edges` required;
      `types`/`meta`/`style` optional, labels fall back to `id` (so the viewer
      renders a plain tree/DAG JSON, not just gdvb captures)
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
- [x] **`gdvb-dirtree-graph` generator** — a non-socket model generator that walks a
      directory tree (nodes = files/dirs/symlinks, edges = containment + distinct
      symlink→target edges) into the same generic model, proving the viewer is
      domain-agnostic. Carries dirtree-specific `style` (exec files, dashed symlinks),
      traversals (Descendants / Path to root), a `directory skeleton` force structure,
      and per-node `size`/`mtime`/`ctime`/`user`/`group`/`perms` metadata. Passing `-`
      reads a newline-separated path list from stdin (ancestors synthesized to connect
      them), so filtering — gitignore, etc. — is delegated to the upstream tool
      (`git ls-files | gdvb-dirtree-graph -`). Originally a `dirtree` subcommand of
      gdvb-render; split out into a standalone script once the "model is the seam"
      architecture was established.
- [x] **`gdvb-sockets-graph` generator + gdvb-render is now a pure viewer.** The socket
      `/proc` capture (the original flagship) was extracted out of gdvb-render into a
      standalone `gdvb-sockets-graph` (filtering flags `--ignore*`, emits JSON to stdout),
      completing the split: **every generator is now standalone** (`gdvb-sockets-graph`,
      `gdvb-dirtree-graph`, `gdvb-cmake-graph`) and **gdvb-render is just the renderer** —
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
- [x] **`gdvb-cmake-graph` generator** (standalone). Reads CMake's File API codemodel-v2
      from a configured build dir and emits the target/dependency/source graph as JSON,
      piped to `render` — the first generator that lives *outside* gdvb-render,
      validating the "model is the seam" architecture. Targets classed by type; `link`
      (target→dep) + `source` (target→file) edges; source nodes start hidden. A real
      dependency DAG, so Topo BFS + "Depended on by" shine.
- [x] **`gdvb-lsp-graph` — LSP call-graph generator** (clangd-first, standalone). Drives a
      language server over stdio JSON-RPC (minimal `Content-Length` client), waits for the
      background index, resolves seeds (`--file` → a file's functions, `--seed NAME` →
      `workspace/symbol`), and walks `callHierarchy/incomingCalls` outward to `--depth`
      (capped by `--max-nodes`) into a caller→callee graph. Nodes classed by SymbolKind
      (function/method/constructor + a `seed` modifier border); Callers/Callees traversals
      + Topo BFS. **clangd 14 only implements incomingCalls** (callers / impact direction;
      outgoingCalls returns empty), and clangd starts indexing only after the first
      `didOpen` — both handled. Verified against `orchard/`.
      Future modes (still open): reference graphs.
- [x] **"Show all" / "Hide all" buttons** on each legend (node classes / edge
      classes) — bulk-set every class in that legend in one click instead of
      per-row toggling; single `applyVis()`/`reheat()` for the whole batch.
- [x] **Any/All visibility toggle** — a per-legend "Match: Any/All" button
      switches that legend's visibility logic between OR (any of an element's
      classes shown keeps it visible — the original/default) and AND (every
      one of its classes must be shown). Independent per legend (`nodeMatchAll`/
      `edgeMatchAll`), since node classes and edge classes have separate
      hide-sets (`visBy` takes the mode as a parameter).
- [x] **`gdvb-dirtree-graph`: "Siblings" traversal** — a new `edge.sibling` class
      chains each directory's children together in label order (O(k) edges per
      directory of k children, not a full O(k²) pairwise mesh); flooding from
      any one child along that chain reaches every sibling without walking
      back up through the parent and down its whole subtree. Hidden by default
      (not a real filesystem relationship, would clutter the skeleton) - still
      traversal-selectable while hidden, since only node visibility gates the
      walk. Synthesized once in `_finalize` from the existing containment
      edges, shared by both the walk and stdin path-list builders.
- [x] **`gdvb-scrub` — redaction filter for safe sharing.** A standalone stdin→stdout
      filter (NOT a generator — deliberately not named `*-graph`, which `bundle-all` globs)
      that reads a model JSON and redacts host-identifying data. Nine ops, all default-on,
      each `--no-<op>`: `ids` (rewrite node ids to opaque `n<i>` + remap edges — ids are
      never displayed/searched/selector-referenced, so this collision-free move strips the
      pid/ip/inode embedded in `p:`/`r:`/`s:` ids), `ips` (non-loopback IPv4/IPv6 →
      placeholder, port kept; loopback-only exemption so private/LAN is still redacted),
      `hostname` (needle from `meta.host`), `users` (socket `user: NAME (uid N)` regex +
      structured `user`/`group`/`uid`/`gid` fields + a name-needle sweep that also catches
      the name embedded elsewhere, e.g. dirtree's `perms user:group` tooltip or a
      `/home/<user>/…` cmdline path; `root`/uid 0 kept), `pids` (remove pids/ppids/
      owner-pids from display — fake numbers were just distracting), `cmdline` (keep argv[0],
      drop args), `unix-paths` (keep
      basename, drop dir), `timestamp` (`meta.captured`→`"n/a"`), `inodes`. Format-aware for
      socket captures (regexes keyed to `gdvb-sockets-graph`'s `proc_*`/`sock_full` templates —
      a documented coupling), graceful on any other model. Closes this item.
- [x] **"Mark" state + "Undirected BFS" static layout for choosing BFS roots** —
      a new `marked` Set, separate from `pinned`, flags selected nodes as layout
      anchors. Deliberately not reusing `pinned`: that's a physics-sim concern
      (freeze position) orthogonal to "seed a layout from here", and conflating
      them would mean a pin set for an unrelated reason silently changes root
      choice later. Named generically ("Mark", not "Root") since not every
      static layout has a notion of roots. Visually composes with Pin instead
      of clobbering it: `pinned` owns `border-*` (dashed amber), `marked` owns
      `underlay-*` (purple halo) - disjoint Cytoscape style properties, so a
      node that's both shows both at once.
      First attempt forced marked nodes to be *additional* roots inside the
      existing directed **Topo BFS** - wrong: containment edges only run
      parent→child, so forward-only BFS from a non-root mark can never reach
      its own ancestors, which then get swept up as a *second*, competing
      layer-0 root, producing edges that visually point backward into the
      "layer 0" mark. Fix: Topo BFS stays purely directed/in-degree-based,
      untouched by marks (it's "roots from edge direction", full stop); marks
      instead drive a new **Undirected BFS** static layout that walks `ADJ`
      (the bidirectional adjacency already built for the topology Select
      tools) instead of directed edges, always seeded from the marked node(s)
      — an undirected walk has no in-degree to fall back on, so the button is
      `disabled` (with a tooltip) until at least one node is marked. The shared
      column/centroid/freeze layout code was factored into `layoutLayers(S,
      layer, label)`, used by both. Verified against real data: marking a
      deep, non-root file now puts its parent exactly 1 undirected hop away and
      the real root at a small positive distance, instead of both mark and
      root fighting over layer 0.
      Second bug (multiple marks): the initial version seeded marks one at a
      time in sort order, each running a *complete* flood before the next mark
      got a turn - so a second mark inside the first mark's connected component
      got swallowed by that flood and ended up at its hop-distance from the
      *first* mark instead of at layer 0, despite being marked itself. Fixed
      with a true multi-source BFS: every marked node is seeded at layer 0
      up front, then flooded once, so each node's layer is its distance to the
      *nearest* mark. Leftover nodes unreachable from any mark (a separate
      component) still get their own arbitrary seed afterward. Verified against
      real data with two marks in the same tree.
- [x] **`gdvb-lsp-graph`: types as first-class nodes.** Every method/constructor
      discovered by the call-graph walk now also pulls in its **owning type**
      (class/struct/interface/enum) as its own node: a `member-of` edge from
      the callable to its type, found via `textDocument/documentSymbol`
      containment (clangd's `CallHierarchyItem` carries no parent-symbol info,
      so the file is scanned once and cached, mapping each member's position to
      its enclosing type). Each newly-discovered type then resolves its
      ancestors/descendants via `textDocument/typeHierarchy` into `inherits`
      edges (derived→base), bounded by the new `--type-depth` (default 3).
      *Supertypes* / *Subtypes* / *Members* / *Owner type* traversals mirror
      the *Callers*/*Callees* pairing. **clangd 14 speaks its pre-3.17 legacy
      `textDocument/typeHierarchy` extension**, not the standardized
      `prepareTypeHierarchy`/`typeHierarchy/supertypes`/`subtypes` trio (same
      generation gap as incomingCalls-only) - one request returns the whole
      ancestor/descendant chain pre-resolved (nested inline), so no iterative
      RPCs are needed to walk it. Verified there's no "wide base class"
      blast-radius risk: a class 20+ subclasses deep off a common base
      (`ISteppable` in `orchard/`) does NOT pull its siblings into the graph,
      because clangd's nested resolution only continues in the direction that
      reached each node (ancestors resolve further ancestors; it doesn't cross
      over to enumerate a common base's other descendants).
- [x] **`gdvb-lsp-graph --all`: whole-project seeding.** Seeds from every function/
      type in the project instead of a specific `--seed`/`--file`: walks every
      source file under the project root (`discover_source_files` - a directory
      walk, not `compile_commands.json`'s TU list, since headers - where most
      classes live - aren't their own translation unit), documentSymbol's each
      one, and adds every callable/type found (callables unmarked - marking
      everything "the seed" is meaningless noise). Skips common vendored-dep
      directory names by default (`third_party`/`vendor`/`external`/…) plus a
      user `--exclude-dir`, since a single vendored header can be tens of
      thousands of lines and would dominate the scan and bury the project's
      own symbols. Also hardened the LSP client for this: **clangd 14's
      `typeHierarchy` has a real crash bug** (segfaults on certain real code -
      confirmed against `orchard/`, not our bug) that kills the whole
      subprocess, not just one request. `LSP` now catches the broken pipe,
      marks itself `crashed`, and treats every further request as "no data"
      instead of raising - so a run degrades to a partial graph with a
      stderr warning instead of crashing. Also reordered type-hierarchy
      expansion to run only *after* the call graph is fully built, so a
      typeHierarchy crash can cost inheritance edges but never the calls.
- [x] **`gdvb-lsp-graph` generalized to any LSP server; `gdvb-clangd-lsp-graph` /
      `gdvb-pyright-lsp-graph` split out.** gdvb-lsp-graph was clangd-first (hardcoded
      `languageId: "cpp"`, a `*.cpp`-only kick-file glob, clangd-specific
      launch flags baked into `main()`). Reworked as a pure LSP *client*: it
      takes `--connect <unix-socket-path>` and never spawns a server at all.
      Rationale (this was a deliberate architecture discussion, not just a
      cleanup): LSP only specifies the JSON-RPC protocol over *some*
      bidirectional stream, not a transport (clangd only speaks stdio; pyright
      also supports node-ipc/TCP) or how to launch a server with the right
      project-specific flags (a C++ `compile_commands.json`, a Python venv) -
      that's a genuinely different problem from "turn documentSymbol/
      callHierarchy responses into a graph," and conflating them was what made
      the file feel C++-shaped. Confirmed a real Unix domain socket
      (`SOCK_STREAM`) is fully bidirectional (unlike a `mkfifo` named pipe,
      which needs two for round-trip) before picking it as the transport.
      Split server orchestration into two new standalone generators,
      `gdvb-clangd-lsp-graph` and `gdvb-pyright-lsp-graph` (deliberately separate
      scripts, not one generic orchestrator + profile table): each spawns its
      server over stdio, bridges that stdio to a fresh Unix domain socket
      (accept one connection, relay both directions on threads), runs
      `gdvb-lsp-graph --connect <socket>` with the same arguments, streams its
      stdout straight through, then tears everything down - not a persistent
      server, same "called with args, JSON pops out" contract as any
      generator. `gdvb-clangd-lsp-graph` owns compile_commands.json autodetection;
      `gdvb-pyright-lsp-graph` just runs `pyright-langserver --stdio`.
      Generalized along the way: `LANG_BY_EXT` + shebang-sniffing (for this
      project's own extensionless scripts) replace the hardcoded `cpp`
      languageId; `discover_source_files` covers any known extension; the
      clangd-specific "latch first $/progress begin token" index-wait became
      a generic progress-quiescence heuristic (works for any server, degrades
      to a flat timeout if a server reports no progress at all); typeHierarchy
      now tries the standardized LSP 3.17 protocol before falling back to
      clangd's extension, gated on the server actually advertising
      `typeHierarchyProvider` (pyright doesn't - skipped with zero wasted
      requests); added `--direction in`/`out`/`both` for call hierarchy
      (clangd 14 only ever returns data for `in`; confirmed pyright implements
      `outgoingCalls` for real by testing it directly).
      Found and fixed one real cross-server bug while verifying against
      pyright: `--all`'s bulk-seeded items were hand-built dicts missing the
      `range` field a real `CallHierarchyItem` has - clangd tolerated that,
      pyright silently no-op'd `incomingCalls`/`outgoingCalls` on them (zero
      call edges came back). Fixed by calling `prepareCallHierarchy` for real,
      like `--seed`/`--file` already did. Verified end-to-end against both
      `orchard/` (clangd, exact node/edge-count regression match against the
      pre-refactor baseline) and a Python project via `pyright` in a venv,
      including dogfooding gdvb-lsp-graph against this repo's own extensionless
      scripts (confirms the shebang-sniffing path).
      Checked whether the two wrappers actually bundle (`just bundle
      gdvb-clangd-lsp-graph`) rather than assuming - they didn't at first, for two
      *compounding* reasons found by actually running the bundled output, not
      just reading the code: (1) `bundle_main.py` captures stdout via
      `contextlib.redirect_stdout`, which only swaps Python's `sys.stdout`
      object - a child spawned with `stdout=None` inherits the real OS file
      descriptor instead, so the model JSON bypassed the capture entirely; (2)
      `main()` called `sys.exit(rc)` even on success, which `bundle_main.py`
      reads as "the generator bailed early (e.g. `--help`) - relay stdout,
      don't render," so it skipped rendering even when everything worked.
      Fixed both: pipe the child's stdout, read it fully, and relay it via
      `sys.stdout.write` (respects a bundle's redirected `sys.stdout`); only
      call `sys.exit` on a genuine failure (`rc != 0`), matching the same
      "return on success" convention (C1) every other generator follows.
      Reverified by actually running both bundled scopes end-to-end (clangd
      against `orchard/`, pyright against a scratch Python project) - both
      produce correct, offline-rendering HTML. Remaining, smaller gap: the
      bundled artifact still needs a separate `gdvb-lsp-graph` reachable at
      runtime (`PATH`, or copied alongside in `dist/`), since these wrappers
      orchestrate it as its own process rather than importing it - so they're
      not *fully* self-contained the way other bundles are, even though they
      now bundle and render correctly.
- [x] **Generalized `just bundle <generator>`** — fuse the viewer + any generator into one
      self-contained runnable script in `dist/` (generate + render in a single invocation).
      Pure shell: cats `gdvb-render` (now entirely under `class Viewer`, so it
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
- [ ] **Multi-host merge**: run `gdvb-sockets-graph` on several machines and combine
      the snapshots into one model, with remote TCP endpoints stitched together
      across hosts (the same conceptual peer, seen from both sides). Leaning
      toward a separate **stitching script** run post-merge (matching remote
      IP:port pairs across snapshots) over baking a hostname into node IDs at
      generation time — deconflicting the id namespace is only one small part
      of the actual stitching problem, so solve them together rather than
      pre-committing to an id scheme now.
- [ ] **Make `gdvb-clangd-lsp-graph`/`gdvb-pyright-lsp-graph` bundles fully dependency-free.**
      They now bundle and render correctly (`just bundle gdvb-clangd-lsp-graph` produces
      working HTML — see the Done entry above), but the bundled artifact still needs
      a separate `gdvb-lsp-graph` reachable at runtime (`PATH` or copied alongside), since
      the wrapper orchestrates it as its own process rather than importing it. Planned
      fix, not yet implemented: mirror how `gdvb-render` embeds Cytoscape.js
      (a blob baked in, decompressed at write time, so it needs zero network refs) —
      have `just bundle` base64-encode `gdvb-lsp-graph`'s source and inject it as a
      `_LSP_GRAPH_SOURCE_B64` constant into the bundle (only for generators that
      reference `find_lsp_graph`, detected the same way the existing C1–C3 lint
      already greps the generator source — so unrelated bundles like
      `gdvb-sockets-graph-scope` stay exactly as lean as today). At runtime,
      `find_lsp_graph()` checks for that constant first, and if present, writes it out
      to the same tmpdir already used (and already cleaned up) for the socket bridge,
      instead of falling through to the PATH/sibling-file lookup it uses standalone.
- [ ] **clangd-driven relationships are incomplete for C++**, inherent to the
      LSP-driven approach: `--depth`/`--max-nodes`-bounded (not exhaustive by
      design — seeded/bounded is the point), and clangd 14's `typeHierarchy` has a
      real crash bug (segfaults on certain real code, confirmed against `orchard/`)
      that silently truncates inheritance data for whatever wasn't resolved before
      the crash. A single seeded, crash-tolerant LSP session is never going to be a
      complete structural picture of a C++ project. See the Doxygen-based generator
      idea below as a more robust complement for structure specifically.
- [ ] **`doxygen-graph` — a generator reading Doxygen XML output**, likely a more
      robust source of C++ *structure* (classes/structs/inheritance/namespaces/
      containment) than driving clangd live, since Doxygen is an offline batch tool
      with no crash-mid-session risk. `orchard/build-debug/share/doc/orchard/xml/`
      already has real output to develop against (confirmed: 749 compounds — classes,
      structs, namespaces, functions, — with `<basecompoundref>` giving inheritance
      directly, and nested `<memberdef>`s giving containment). Confirmed this
      particular build did NOT enable `REFERENCED_BY_RELATION`/`REFERENCES_RELATION`
      (no `<references>`/`<referencedby>` elements present), so it has no call-graph
      data — this generator would be structure-only, complementing gdvb-lsp-graph's call
      graphs rather than replacing them. Would need the same non-first-party
      filtering as the item below (confirmed the index mixes `orchard::Angle`
      alongside nlohmann/json's `adl_serializer` and `detail::actual_object_comparator`,
      since vendored headers sit directly under `src/`).
- [ ] **Exclude non-first-party content (stdlib/vendored libs) generally**, not just
      per-generator ad hoc: `gdvb-lsp-graph --all` already skips common vendor directory
      names by default plus `--exclude-dir`, but confirmed the same leak in Doxygen
      XML (see above) — a project's own namespace mixed in with a vendored
      single-header library's internals, with no structural distinction from the
      data alone (both just look like "a class/struct in some file"). Worth a
      shared, consistent convention/mechanism across generators (gdvb-dirtree-graph,
      gdvb-cmake-graph, gdvb-lsp-graph, the future doxygen-graph) rather than reinventing
      filtering per generator - e.g. a common notion of "project root vs. everything
      under it" plus name-based heuristics, or leaning on each ecosystem's own
      first-party marker where one exists (a compile_commands.json entry's directory
      being under the project root vs. a system include path, etc.).
- [ ] Add a generator that reads a GraphViz dot file and adapts it to this JSON format
- [ ] Add a generator that reads a PlantUML component diagram (this is probably the only one that maps decently) and adapts it to this JSON format

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
- [ ] A common workflow is to isolate sets manually and run the static layouts
      to organize sets of interest. Afterwards it would be nice to leave those
      alone but run static layouts on the rest. We can use the pin state for
      this so that static layout ignores pinned units.

## Sharing / packaging

- [x] Pick a **license** (MIT) and add `LICENSE`.
- [x] Add a **"Similar Projects/Tools"** section to the README (positioning vs.
      Weave Scope, EtherApe, bandwhich/nethogs, Hubble/Pixie, etc.).
- [ ] Keep the comparison **current** — recheck periodically; notable opening:
      Weave Scope is unmaintained since ~2021, so there's room for a modern,
      agentless single-host take. Watch new entrants (e.g. grigio/network-monitor, 2025).
- [ ] Add a **screenshot / short GIF** to the README.
- [ ] Easy install story (download URL / release); shebang + `chmod +x` already work.
- [ ] `CHANGELOG.md` + version string.
- [ ] **Document the JSON schema** (`SCHEMA.md`): the generic typed-directed-graph
      model, so other tools can produce/consume it. This is *the* ecosystem seam
      (generators emit JSON and pipe to `render`; they don't import gdvb-render).
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
