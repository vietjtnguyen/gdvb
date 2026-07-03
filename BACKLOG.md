# gdvb — backlog

Running list of ideas — not commitments. Completed work has been removed; it lives in git history (and the README) rather than here.

Each item carries a rough priority: **[very high]** / **[high]** / **[med]** / **[low]**, split as **[low now / high later]** where the value depends on the model settling first. **[?]** marks an item that still needs clarification or expansion before it's actionable — see the notes on each. Items are grouped by the generator they belong to, plus cross-cutting sections for the viewer, the schema, quality, and packaging. Within a section they're ordered high → low.

## Generator — gdvb-sockets-graph

- **[high]** **Multi-host merge**: run `gdvb-sockets-graph` on several machines and combine the snapshots into one model, with remote TCP endpoints stitched together across hosts (the same conceptual peer, seen from both sides). Leaning toward a separate **stitching script** run post-merge (matching remote IP:port pairs across snapshots) over baking a hostname into node IDs at generation time — deconflicting the id namespace is only one small part of the actual stitching problem, so solve them together rather than pre-committing to an id scheme now.
- **[med]** Listening **backlog / queue depths** and more socket detail in tooltips.
- **[med]** **Big-endian** support: `/proc/net` addresses are host byte order, decoded assuming little-endian. Detect host endianness (e.g. `sys.byteorder`) and handle big-endian (s390x) so IP text is correct there too.
- **[low]** Optionally cross-check counts against `ss`/`lsof` when present.
- **[low]** Collapse the **same-path connected-UNIX "accept storm"** (e.g. the D-Bus system bus spawns hundreds of identical connected endpoints) into a single node with a count, or group them under their listener.
- **[low]** **Container grouping**: label/group processes by cgroup/container.
- **[?]** Link UNIX-domain socket **peers**. `/proc/net/unix` lists each UNIX socket but not which two endpoints form a connected pair; `ss -xp` exposes the peer linkage (the `Peer` inode), so the two ends of a connected pair could be joined by an edge. Optional, only if `ss` exists. *Flagged: confirm the goal is drawing the peer→peer edge, and that it's worth the `ss` dependency.*
- **[?]** **Network-namespace awareness**: a network namespace is an isolated copy of the network stack (its own interfaces, routing, socket tables) — containers and some sandboxes each run in their own. Today the capture only sees the netns it runs in. Item: note which netns was captured, and optionally enumerate/visit the others. *Flagged: confirm scope — just labelling the captured netns, or actually crossing into others.*
- **[?]** IPv6 link-local **scope id** handling. Link-local addresses (`fe80::/10`) are only meaningful paired with an interface "zone" (e.g. `fe80::1%eth0`); `/proc/net/tcp6` carries that as a numeric interface index we currently drop. Item: decode and surface it so link-local endpoints are disambiguated. *Flagged: confirm this matters for the target hosts.*

## Generator — gdvb-lsp-graph (clangd / pyright wrappers)

- **[med]** **Make `gdvb-clangd-lsp-graph` / `gdvb-pyright-lsp-graph` bundles fully dependency-free.** They now bundle and render correctly, but the bundled artifact still needs a separate `gdvb-lsp-graph` reachable at runtime (`PATH` or copied alongside), since the wrapper orchestrates it as its own process rather than importing it. Planned fix, not yet implemented: mirror how `gdvb-render` embeds Cytoscape.js (a blob baked in, decompressed at write time, zero network refs) — have `just bundle` base64-encode `gdvb-lsp-graph`'s source and inject it as a `_LSP_GRAPH_SOURCE_B64` constant into the bundle (only for generators that reference `find_lsp_graph`, detected the same way the existing C1–C3 lint already greps the generator source — so unrelated bundles stay as lean as today). At runtime, `find_lsp_graph()` checks for that constant first and, if present, writes it out to the same tmpdir already used (and cleaned up) for the socket bridge, instead of falling through to the PATH/sibling-file lookup it uses standalone.
- **[low]** **clangd-driven relationships are incomplete for C++** — a known limitation of the LSP-driven approach, tracked for expectations rather than as a fix: `--depth`/`--max-nodes`-bounded (seeded/bounded is the point, not exhaustive), and clangd 14's `typeHierarchy` has a real crash bug (segfaults on certain real code, confirmed against `orchard/`) that silently truncates inheritance data for whatever wasn't resolved before the crash. A single seeded, crash-tolerant LSP session is never a complete structural picture. The `doxygen-graph` idea below is the more robust complement for structure specifically.

## New generators (proposed)

- **[high]** Generator that reads a **GraphViz `.dot`** file and adapts it to this JSON model.
- **[high]** Generator that reads a **PlantUML component diagram** (probably the only PlantUML diagram type that maps decently) and adapts it to this JSON model.
- **[med]** **`doxygen-graph` — a generator reading Doxygen XML output**, likely a more robust source of C++ *structure* (classes/structs/inheritance/namespaces/containment) than driving clangd live, since Doxygen is an offline batch tool with no crash-mid-session risk. `orchard/build-debug/share/doc/orchard/xml/` already has real output to develop against (confirmed: 749 compounds — classes, structs, namespaces, functions — with `<basecompoundref>` giving inheritance directly, and nested `<memberdef>`s giving containment). This particular build did NOT enable `REFERENCED_BY_RELATION`/`REFERENCES_RELATION` (no `<references>`/`<referencedby>` elements), so it has no call-graph data — this generator would be structure-only, complementing gdvb-lsp-graph's call graphs rather than replacing them. Needs the same non-first-party filtering as the cross-cutting item below (the index mixes `orchard::Angle` alongside nlohmann/json's `adl_serializer`, since vendored headers sit directly under `src/`).

## Cross-cutting (all generators)

- **[med]** **Exclude non-first-party content (stdlib / vendored libs) generally**, not per-generator ad hoc: `gdvb-lsp-graph --all` already skips common vendor directory names by default plus `--exclude-dir`, but the same leak shows up in Doxygen XML (above) — a project's own namespace mixed in with a vendored single-header library's internals, with no structural distinction from the data alone. Worth a shared, consistent convention across generators (gdvb-dirtree-graph, gdvb-cmake-graph, gdvb-lsp-graph, the future doxygen-graph) rather than reinventing filtering per generator — e.g. a common notion of "project root vs. everything under it" plus name heuristics, or leaning on each ecosystem's own first-party marker where one exists (a compile_commands.json entry's directory under the project root vs. a system include path, etc.).

## Viewer / UX

- **[very high]** **Static layout that ignores pinned units.** A common workflow is to isolate sets manually and run the static layouts to organize sets of interest, then leave those alone while re-running static layout on *the rest*. Use the existing pin state for this: static layout skips pinned nodes.
- **[high]** **Per-class counts** in the legend (e.g. how many nodes/edges of each class).
- **[med]** Search results **navigation** (next/prev, center on a match).
- **[med]** **Keyboard shortcuts** (`/` focus search, `esc` clear, `f` fit, …).
- **[med]** **Node sizing** encodes a metric (socket count, connection count).
- **[low now / high later]** **Visualization layers** — a first-class JSON concept alongside `style` / `traversals` / `force_structures` that activates data→appearance mappings: map a numeric node field to a colormap (`size` → fill, `mtime` → heat), or scale node size by a metric, toggleable from a viewer control. dirtree already emits the numeric fields (`size`, `mtime`, `ctime`) such a layer would consume; sockets could expose connection/socket counts the same way.
- **[low]** **jq-style query box** over the embedded JSON objects — a power-user complement to the substring/regex search (natural now that the data is one clean JSON model in the page).
- **[low]** Export the current view as **PNG/SVG** (the browser can already do most of this).
- **[low]** **Persist UI state** (filters, pins, node positions) across re-runs (localStorage and/or encoded in the file).
- **[low]** Optional **dark mode** (the current light theme is an intentional design choice — only if there's demand).
- **[low]** **Diff two snapshots** to highlight what changed since last capture — though a generic JSON diff tool may cover this without viewer support.
- **Traversal-tool polish** (framework exists; expose in UI):
  - **[low]** surface `mode:step` + `deselectSource` (walk) + `recenter` as per-tool UI toggles / a "Traverse settings" row (currently data-only).
  - **[low]** hop-limit / depth knob (generalize `step` to N hops).
  - **[low]** **export the current selection / traced set** (JSON/CSV).
  - **[low now / med later]** simple in-viewer editor to add/tweak a traversal rule live.
  - **[?]** seed inward from a remote. Already expressible as data (a traversal rule with `dir:"in"`). *Flagged: clarify what's actually wanted beyond that — a built-in UI tool, a socket-specific default, or something else.*

## Schema / ecosystem seam

- **[high — once the model settles]** **Document the JSON schema (`SCHEMA.md`)**: the generic typed-directed-graph model, so other tools can produce/consume it. This is *the* ecosystem seam (generators emit JSON and pipe to `render`; they don't import gdvb-render). Held until the model settles — recent refactors (multi-class `node_classes`/`edge_classes`) reshaped it, and an earlier draft was removed for going stale. Give it a bit more time, then write it.

## Quality / engineering

- **[high]** **Tests** for the `/proc` parsers (fixture-based) + minimal CI.
- **[med]** **Harden JSON-supplied `style`** for untrusted snapshots: strip/deny external references (`background-image: url(http…)`, web fonts) so `render` can't be coerced into a network fetch, preserving the offline guarantee.
- **[low]** **Performance**: replace the O(N²) repulsion with a Barnes-Hut/quadtree approximation for very large hosts; cap/warn on huge graphs.

## Sharing / packaging

- **[high — human will do]** Add a **screenshot / short GIF** to the README.
