# socketscope

**See every open socket on a Linux host and the processes behind them — as one interactive, offline graph.**

socketscope is two parts: small **generator** scripts that snapshot something into a generic JSON graph model, and **`render-graph-html.py`**, a domain-agnostic **viewer** that renders any such model into a **single self-contained HTML file**. Open it in any browser — no server, no internet, no install — and explore the graph: search, filter, trace dependencies, lay it out.

The flagship generator, **`sockets-graph`**, captures every socket on a machine (TCP, UDP, UNIX-domain), the processes using them, and the process tree — so you can see who's listening, who's connected to whom, and how data flows between processes. Other generators ship too (`dirtree-graph`, `cmake-graph`), and writing your own is just emitting the JSON shape.

Everything is plain Python with **zero dependencies** (standard library only); the visualization library is vendored into the viewer, so its HTML works completely offline.

```bash
sudo python3 sockets-graph | python3 render-graph-html.py > sockets.html
# then open that file in your browser
```

---

## Why

`ss`, `lsof`, and `netstat` give you a flat list of sockets. Great for grepping, bad for *seeing structure*: which process owns a listener, which connections are loopback chatter between two local services, what a daemon actually talks to. socketscope turns that flat list into a force-directed graph you can search, filter, and trace through — so the shape of the system becomes obvious at a glance.

## Requirements

- **Python 3.6+** — standard library only, nothing to `pip install`. The viewer
  (`render-graph-html.py`) runs anywhere Python does.
- **Linux** for `sockets-graph` (it reads `/proc`); other generators have their own
  needs (`cmake-graph` wants `cmake` on PATH).
- A browser to open the result. The HTML is fully offline.

## Install

There's nothing to install — they're plain scripts with no dependencies. Copy the viewer
(`render-graph-html.py`) and whichever generators you want onto the host:

```bash
sudo python3 sockets-graph | python3 render-graph-html.py > sockets.html
```

Optionally make them executable (`chmod +x sockets-graph render-graph-html.py`). Run `sockets-graph` with `sudo` for
full visibility (see below).

## Usage

A **generator** emits the JSON model to stdout; the **viewer** reads it (stdin or a file)
and writes the HTML:

```bash
sudo sockets-graph | render-graph-html.py > sockets.html       # sockets + processes
sudo sockets-graph --ignore-uds | render-graph-html.py -o net  # less noise -> net.html
sockets-graph | jq .                                     # the model is just JSON
dirtree-graph ~/project | render-graph-html.py > tree.html     # a directory tree
cmake-graph build       | render-graph-html.py > cmake.html     # CMake targets/deps
```

`render-graph-html.py` reads the model from **stdin** (default) or a **file argument**, and
writes HTML to **stdout** unless you pass `-o NAME` (→ `NAME.html`). It polls nothing and
needs no privileges — only the generator does. Save a generator's JSON to re-view or share later;
because the model fully determines the output, rendering the same model always produces the
same HTML.

**Run `sockets-graph` as root (`sudo`) for the full picture.** Unprivileged, the kernel
only lets you see the file descriptors of your *own* processes, so most sockets can't be
attributed to a process. It still works — it just shows less, and reports on stderr how
many sockets it couldn't attribute. It's a **snapshot** — re-run any time to refresh.

The generators print a one-line summary to **stderr**, keeping stdout clean for the pipe;
the viewer's "Download data (JSON)" button re-exports the embedded `{meta, node_classes,
edge_classes, style, edge_key, traversals, force_structures, nodes, edges}` model.

### Other generators (the model is the seam)

The viewer renders one generic JSON model, so **anything that emits that shape can be
visualized**. `sockets-graph` (above) is one such standalone generator; here are the
others that ship. They each build the model and pipe it to the viewer, importing nothing
from it — the JSON model is the only contract.

**`dirtree-graph`** — walk a directory into the model: nodes are directories, files,
and symlinks; edges are parent→child containment plus a **distinct dashed edge** from each
symlink to its target. Executable files get a green border; it ships **Descendants**,
**Children** (one level down), **Parent** (one level up), **Path to root**, and
**Siblings** (same immediate parent) traversals plus a **directory skeleton** force
structure, and each node carries `size`/`mtime`/`ctime`/owner/`perms` in its tooltip.

```bash
dirtree-graph ~/project | render-graph-html.py > tree.html
dirtree-graph / --max-depth 3 | render-graph-html.py      # shallow, whole-system
dirtree-graph . --no-files  | render-graph-html.py        # directories only
```

Pass `-` as the path and it reads a newline-separated path list from **stdin** instead of
walking, synthesizing the ancestor directories needed to connect them — so filtering
(gitignore, etc.) is delegated to whatever upstream tool already knows which paths matter.
Relative entries resolve against **`-C`/`--directory`** (which also becomes the root) —
needed for `git ls-files`, whose paths are relative to the repo root:

```bash
git -C ~/p ls-files | dirtree-graph - -C ~/p | render-graph-html.py   # Git-tracked only
find . -name '*.py'  | dirtree-graph -        | render-graph-html.py
```

**`cmake-graph`** — read a CMake project's [File API](https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html)
and emit the target/dependency/source graph:

```bash
cmake-graph build | render-graph-html.py > cmake.html   # targets, deps, source files
cmake-graph build --no-sources | render-graph-html.py   # just the dependency DAG
```

Targets are colored by type (executable / static-library / …), edges are `link`
(target→dependency) and `source` (target→file); it's a real dependency **DAG**, so the
**Topo BFS** static layout and the *Depended on by* traversal (impact analysis) are the
natural tools. Source-file nodes start hidden — toggle the **source** node class on to
reveal them; CMake-internal `.rule`/generated stubs are split into a separate, also-hidden
**generated** class.

**`lsp-graph`** — drive a language server ([clangd](https://clangd.llvm.org/) by default)
and emit a **call graph**. It walks the call hierarchy (`callHierarchy/incomingCalls`)
outward from one or more seed symbols:

```bash
lsp-graph proj --file src/foo.cpp | render-graph-html.py > calls.html   # seed: a file's functions
lsp-graph proj --seed planPath --depth 4 | render-graph-html.py         # seed: a symbol name
```

Nodes are functions/methods/constructors (seeds get a red border), edges are directed
caller→callee, so the *Callers* / *Callees* traversals do impact analysis and **Topo BFS**
lays the call graph out by depth. It's bounded by `--depth` (default 3) and `--max-nodes`.
The graph is built from **callers** (`incomingCalls`) — the "what breaks if I change this"
direction — because clangd doesn't implement outgoing call hierarchy. Needs `clangd` on
PATH and a `compile_commands.json` (autodetected under `<proj>/build*`).

Every method/constructor also pulls in its **owning type** (class/struct/interface/enum)
as its own node — a `member-of` edge to the type it belongs to (`textDocument/documentSymbol`
containment), plus the type's ancestors/descendants (`textDocument/typeHierarchy`) as
`inherits` edges, bounded by `--type-depth` (default 3). *Supertypes* / *Subtypes* /
*Members* / *Owner type* traversals navigate this the same way *Callers*/*Callees* do calls.

### Filtering at capture time

`sockets-graph --ignore` drops node classes from the data entirely (smaller file, less clutter). You can also just hide/show classes live in the viewer's legend after the fact. Class ids: `proc-root`, `proc-user`, `proc-kernel`, `tcp`, `udp`, `unix`, `unix-unnamed`, `remote`. Run `sockets-graph --help` for the convenience flags (`--ignore-uds`, `--ignore-kernel`, …).

## Exploring the graph

Each **node** is a process (blue = user, red = root, grey = kernel thread) or a socket (green TCP, gold UDP, purple UNIX) or a remote endpoint (pink). **Edges** are directed: process → its sockets → the peers/remotes they connect to, plus the process tree (grey "parent of" arrows). Listening sockets get a bold border, so service hubs stand out.

The graph self-organizes with a live force simulation that settles and stops. Then:

- **Search** — match nodes across all their text (command line, address, inode, type). Space-separated terms are AND'd; wrap in `/…/` for a regex (`/:(80|443)\b/`, `/sshd/i`). Matches become the selection.
- **Select** — generic topology tools that operate on the current selection: All / None / Invert, **Grow** (add neighbours), **Shrink** (erode — drop nodes touching the outside), **Walk** (step outward, drop the source), **Component** (whole connected group). Useful on *any* graph; no domain knowledge.
- **Trace chain** — the killer feature, and now a **data-driven traversal tool** (a `Traverse` button) rather than hardcoded. Select a process (or socket, or search result) and trace the connected **data chain**: it follows sockets *laterally* to other processes that share them and *down* to child processes — but never *up* to parents, so it won't climb to `init` and swallow the whole host. Its behavior is just a rule in the JSON (`{edge:"edge.tree",dir:"out"}, {edge:"edge.io",dir:"both"}`), so a graph can ship its own traversals (see Styling/Schema). Search `tcp`, hit Trace, and watch the related processes light up.
- **Pin** — freeze selected nodes in place (they still exert forces, so they anchor their neighbors). Pin a hub or a chain and let the rest settle around it.
- **Mark** — flag selected nodes as layout anchors, independent of Pin (a physics concern) — a purple halo, composable with Pin's dashed border. The **Undirected BFS** static layout requires at least one mark (it's disabled until then) and always seeds from it, since an undirected walk has no in-degree to pick a root from the way the directed **Topo BFS** layout does.
- **Force structure** — how the layout's springs are weighted (a data-driven dropdown). socketscope ships **process tree** (cluster by ancestry) and **data flow** (cluster by socket connectivity); every graph also gets the built-in **spread** (all edges equal) and **distance from selected** (concentric rings of hop-distance). A **strength** slider scales the emphasis.
- **Filter** — two legends (**Node classes** and **Edge classes**) whose swatches show/hide by class. Nodes and edges each carry a *set* of classes (multi-membership), and visibility is **OR**: an element hides only when *all* its classes are off (so hiding the `file` edge class thins a dirtree to its directory skeleton, while an executable file stays visible via its `executable` class). **Kernel threads and UNIX-domain sockets start hidden** by default (the noisy bulk); which classes start hidden is data-driven (a `"hidden": true` flag on the catalog entry), not hardcoded. Classes not in the catalog collapse into an `other` row.
- **Pan/zoom** freely, **drag** nodes (they pin while held), **hover** for full details (cmdline, addresses, owners), click a node to isolate its neighbourhood.
- **Download data (JSON)** — export the captured graph model (nodes, edges, meta) for use elsewhere.

## A note on sharing the output

A sockets graph embeds a detailed picture of the host: process command lines (which can include arguments, paths, sometimes secrets), local and remote IP addresses, and UNIX socket paths. **Treat `sockets.html` like the sensitive snapshot it is** — it's git-ignored by default for that reason. Filter with `sockets-graph --ignore` to drop whole node classes, and/or run the snapshot through **`scrub-model`** before sharing externally.

`scrub-model` is a redaction **filter**: it reads a model JSON on stdin, redacts host-identifying data, and writes the scrubbed model to stdout, so it drops straight into the pipe:

```bash
sockets-graph | scrub-model | render-graph-html.py > safe.html
scrub-model < snapshot.json | render-graph-html.py            # a saved snapshot
```

Nine scrub operations run by default (each disableable with `--no-<op>`): **ids** (rewrite node ids to opaque tokens — they're never displayed, so this strips the pid/ip/inode embedded in them), **ips** (non-loopback IPv4/IPv6 → placeholder, port kept; loopback and private/LAN handling is deliberate — private ranges *are* redacted), **hostname**, **users** (usernames/uids, keeping `root`), **pids** (remove pids/ppids and the socket `owners:` line — ownership is still shown by the edges), **cmdline** (keep the program, drop its args), **unix-paths** (keep basename, drop directory), **timestamp**, **inodes**. It's format-aware for socket captures but degrades gracefully on any model (the socket-specific ops simply match nothing).

## How it works

`sockets-graph` builds the graph model:

1. Reads processes from `/proc/<pid>/{status,cmdline}` and the parent/child tree.
2. Parses sockets from `/proc/net/{tcp,tcp6,udp,udp6,unix}` (handling the little-endian address quirks itself — no dependency on `ss`/`lsof`).
3. Maps sockets to processes via `/proc/<pid>/fd/` (`socket:[inode]` links).
4. Emits the model as JSON. `render-graph-html.py` then embeds it in an HTML page whose viewer (Cytoscape.js, vendored inline) renders and explores it.

Cytoscape.js is bundled into the viewer as a compressed blob and decompressed at write time, so the output has **zero network references** and opens offline anywhere.

## Bundling

The viewer and a generator are normally two scripts joined by a pipe
(`generator | render-graph-html.py`). `just bundle` fuses them into **one
self-contained, runnable script** — generate *and* render in a single invocation,
nothing to pipe:

```sh
just bundle sockets-graph                        # -> dist/sockets-graph-scope
sudo ./dist/sockets-graph-scope > sockets.html   # capture + render in one shot
sudo ./dist/sockets-graph-scope -o sockets       # write sockets.html directly

just bundle dirtree-graph                        # -> dist/dirtree-graph-scope
just bundle lsp-graph calls                       # custom output name
just bundle-all                                  # every generator -> dist/
```

Bundles land in `dist/` (git-ignored). The recipe is plain shell: it cats the
viewer (everything lives under one `class Viewer`), then the generator, then a
small glue tail, and runs `black`. At runtime the glue calls the generator's
`main()`, captures the model JSON it writes to stdout, and hands it to
`Viewer.emit_html`. So a bundle accepts all of the generator's own flags
(`--ignore-uds`, `--depth`, …) **plus** a bundle-provided `-o NAME` for the HTML
output (stdout by default); `-h`/`--help` shows the generator's own help.

### Naming

The scripts follow POSIX program naming — **lowercase kebab-case with no `.py`
extension** — even though they're Python (a `#!/usr/bin/env python3` shebang makes
them directly runnable, e.g. `./sockets-graph`):

- **generators** are `{subject}-graph`: `sockets-graph`, `dirtree-graph`,
  `cmake-graph`, `lsp-graph`.
- **bundles** are `{subject}-graph-scope` — the generator and viewer fused into one
  ("-scope" as in *socketscope*). `just bundle sockets-graph` → `dist/sockets-graph-scope`.
- the **viewer** is `render-graph-html.py`.

### Generator conventions

Any generator can be bundled (and piped) if it follows these — every shipped
generator does:

- **C1 — stdout is the model.** A top-level `main()` builds the graph-model dict
  and writes it as JSON to **stdout** (`json.dump(model, sys.stdout, …)`), and
  *returns* on success. Diagnostics go to stderr.
- **C2 — `-o`/`--out` is reserved** for the bundle's HTML output; don't define it.
- **C3 — don't define a top-level `Viewer`.** That one name is the renderer's
  namespace (the only name a generator must avoid); everything the viewer exposes
  is a `Viewer.*` attribute.
- **C4 — errors via `SystemExit`.** Raise `SystemExit("message")` (or let argparse
  exit) on failure / `--help`; the bundle relays the message and exit code instead
  of trying to render. The success path just returns.

`just bundle` lints C1–C3 and refuses a generator that violates them.

## Styling

Appearance is built from layered [Cytoscape stylesheets](https://js.cytoscape.org/#style), applied in order:

1. **Base** — baked into the viewer and strictly **domain-agnostic**: structure only (rectangles, labels-inside, sizing, arc edges + arrowheads, neutral greys). No class colors and no socketscope-specific fields. So *any* directed graph renders as readable labelled rectangles rather than bare dots.
2. **Class colors** — generated at runtime from `node_classes[]` / `edge_classes[]`: one rule per class (`node.tcp { background-color: … }`, `edge.io { line-color: … }`). The catalogs are therefore the **single source** for both the legend swatch *and* the element color, so they can't drift — recolor a class by editing its catalog entry and both update together. Each entry may carry `"hidden": true` to start that class unchecked. Because nodes/edges hold a **set** of classes, rules **compose** (a node that is both `file` and `executable` gets the `file` fill *and* the `executable` border); a class with no `color` is a pure modifier (e.g. `executable` contributes only its border). (Empty when a graph supplies no catalogs.)
3. **Snapshot `style`** — a top-level `style` array in the JSON (a Cytoscape stylesheet). A socketscope capture **prepopulates** this with its *domain* styling — the `node[listen = "yes"]` hub border and the `io`/`tree` edge colors — because those reference fields a generic graph wouldn't have. Edit it (or add your own) and `render` to restyle without touching code; a generic graph simply omits it.
4. **Interaction states** — selection, traced chain, pinned, faded — owned by the viewer and applied last, so a snapshot's `style` can restyle the graph but can't break selection/trace/pin.

A top-level **`edge_key`** (a list of plain-text lines) populates the viewer's "Edge style" key — domain text like `→ arrowhead = direction`. It's optional; a graph that omits it hides the section.

A top-level **`traversals`** array defines the **Traverse** tools (the buttons that grow the selection by rule). Each is `{id, label, mode:"flood"|"step", deselectSource?, recenter?, rules:[…]}`, and a rule is `{source?, edge?, target?, dir}` where each slot is a Cytoscape selector (omitted = match anything; slots AND, rules OR) and `dir` ∈ `out`/`in`/`both` relative to edge orientation. socketscope ships one tool — "Trace chain" (`tree` edges `out`, `io` edges `both`); any graph can define its own. The built-in **Select** tools (Grow/Shrink/Walk/Component/…) need no data and always work.

A top-level **`force_structures`** array defines the **Force structure** dropdown (how the layout weights its springs). Each is `{id, label, emphasize}` where `emphasize` is an edge selector; when active, matching edges spring strongly (strength-scaled) and the rest weakly, so the layout clusters around them. socketscope ships `tree`/`flow`; the viewer always adds built-in **spread** and **distance from selected**, so a graph that omits it still lays out.

Because the base is fully generic and the viewer only requires `nodes` + `edges`, it doubles as a renderer for **any directed graph** — hand a `{ "nodes": [...], "edges": [...] }` file (a tree, a dependency graph, …) to `render-graph-html.py` and it draws. `node_classes`, `edge_classes`, `meta`, `style`, `edge_key`, `traversals`, and `force_structures` are all optional; nodes fall back to their `id` for a label, and any class not in a catalog shows up under the legend's `other` row.

(Note: a hand-edited override `style` that references an external `url(...)` or web font would fetch over the network when rendered — see BACKLOG; the built-in base + class colors contain no external references.)

## Compatibility

socketscope deliberately depends on very little, and on nothing *new*.

- **No external tools.** It never shells out to `ss`, `lsof`, `netstat`, or anything else — it reads `/proc` directly. So there's no dependency on `iproute2`/`net-tools` versions, and it runs on stripped-down systems (minimal containers, embedded, rescue shells) that don't ship those binaries.
- **Python 3.6+**, standard library only. No `pip install`, no virtualenv.
- **Kernel / `/proc`.** It uses only long-stable interfaces — `/proc/<pid>/{status,cmdline,fd}` and `/proc/net/{tcp,tcp6,udp,udp6,unix}`. Those formats have been stable for ~20 years, so essentially any modern Linux kernel works. There's **no dependency on recent kernel features** (no eBPF, no cgroup v2, no new syscalls).
- **CPU architecture: little-endian.** `/proc/net` prints socket addresses in host byte order, and socketscope decodes them assuming little-endian — correct on x86/x86-64, ARM/ARM64, RISC-V, i.e. effectively every common Linux machine. On a **big-endian** host (e.g. s390x), IP-address *text* would render wrong, though the graph structure and port numbers are still correct.
- **Privileges.** Run as root for full process↔socket attribution. Unprivileged (or under `hidepid=` mounts / hardened `/proc`) it sees only your own processes' descriptors; it degrades gracefully and reports how many sockets it couldn't attribute.
- **The HTML viewer** needs a modern evergreen browser — Chrome/Edge, Firefox, Safari, roughly **2019 or newer** (it uses `Object.fromEntries`, `Blob` / `URL.createObjectURL`, and Cytoscape.js 3.30). No Internet Explorer. Nothing loads over the network, so air-gapped machines are fine.

## Limitations

- It's a **snapshot**, not a live monitor.
- `/proc/net` is **network-namespace scoped** — you see the namespace the script runs in (run it inside a container/netns to see that one).
- UNIX socket **peer** links aren't exposed by `/proc/net/unix`, so two ends of a UNIX pair aren't connected by an edge (loopback TCP pairs *are*).

## Similar Projects/Tools

socketscope is a graph viewer (one offline HTML file) fed by generator scripts. No single
tool occupies the same spot, but each part of it has well-established neighbours. Grouped
by how they relate:

**Turning a graph into a standalone interactive HTML.** [pyvis](https://pyvis.readthedocs.io/)
renders a NetworkX graph to an interactive HTML page (vis.js) you open in a browser — the
same "a file, not a server" shape. It's a library you script against; styling is set when
you build the page, and there's no generic-model/generator split.

**Graphviz and interactive front-ends for it.** [Graphviz](https://graphviz.org/)/DOT is the
standard for laying a graph out from text; DOT mixes the graph with its layout and style
directives, and renders to static images by default. Interactive front-ends exist —
[d3-graphviz](https://github.com/magjac/d3-graphviz) (Graphviz compiled to WASM, in-browser
with zoom/pan) and the desktop `xdot`. socketscope keeps the data and the (ignorable) style
hints in separate parts of the JSON rather than in one DSL.

**Interactive graph explorers.** [Gephi](https://gephi.org/) and the desktop
[Cytoscape](https://cytoscape.org/) load a graph file (GraphML/GEXF/CX) into a full GUI for
layout and analysis — more analytical power, but installed applications working on files
rather than a self-contained artifact. (socketscope embeds the Cytoscape.js *library* for
rendering.)

**Diagram-as-code.** [Mermaid](https://mermaid.js.org/), [D2](https://d2lang.com/),
[PlantUML](https://plantuml.com/), and [Kroki](https://kroki.io/) (a renderer for many of
them) are text DSLs that produce diagrams, some with interactive viewers; the DSL generally
ties the data to its presentation. [Structurizr](https://structurizr.com/) (C4) is the
exception — it separates a model from the views that select and style it, similar in spirit
to the data/hints split here, but scoped to software architecture.

**Data separate from a visualization spec.** GraphML with an external stylesheet, and
[Vega](https://vega.github.io/)/Vega-Lite's declarative encoding over raw data, embody the
same "data plus a separable, ignorable spec" idea; neither is a turnkey graph explorer.

**Code-structure graphs** (overlapping `cmake-graph` / `lsp-graph`).
[Sourcetrail](https://github.com/CoatiSoftware/Sourcetrail) was an interactive symbol /
call-graph explorer (a desktop app that indexes code; discontinued and open-sourced).
[Doxygen](https://www.doxygen.nl/) emits call/include graphs as static Graphviz images
alongside HTML docs.

**For `sockets-graph` specifically.** [Weave Scope](https://github.com/weaveworks/scope)
graphed process/container connections from `/proc`+conntrack (agent + server, now
unmaintained); [EtherApe](https://etherape.sourceforge.io/) draws live host-traffic graphs;
`bandwhich`/`nethogs`/`iftop` list live per-process connections; Sysinternals TCPView +
Process Explorer cover the same ground on Windows; [Cilium Hubble](https://github.com/cilium/hubble)
and [Pixie](https://px.dev) build eBPF service maps at cluster scale. Those observe *live*
network state; `sockets-graph` takes a one-shot `/proc` snapshot.

What's specific to socketscope is the combination rather than any one capability: a static
offline bundle, interactive exploration, data kept separate from ignorable viz hints, and a
pipe-friendly generator/viewer split. Each of those exists elsewhere.

## License

socketscope is released under the [MIT License](LICENSE). It bundles [Cytoscape.js](https://js.cytoscape.org/) (also MIT), whose attribution is preserved inside the script.
