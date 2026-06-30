# socketscope

**See every open socket on a Linux host and the processes behind them — as one interactive, offline graph.**

socketscope is two parts: small **generator** scripts that snapshot something into a generic JSON graph model, and **`socketscope.py`**, a domain-agnostic **viewer** that renders any such model into a **single self-contained HTML file**. Open it in any browser — no server, no internet, no install — and explore the graph: search, filter, trace dependencies, lay it out.

The flagship generator, **`sockets_graph.py`**, captures every socket on a machine (TCP, UDP, UNIX-domain), the processes using them, and the process tree — so you can see who's listening, who's connected to whom, and how data flows between processes. Other generators ship too (`dirtree_graph.py`, `cmake_graph.py`), and writing your own is just emitting the JSON shape.

Everything is plain Python with **zero dependencies** (standard library only); the visualization library is vendored into the viewer, so its HTML works completely offline.

```bash
sudo python3 sockets_graph.py | python3 socketscope.py > sockets.html
# then open that file in your browser
```

---

## Why

`ss`, `lsof`, and `netstat` give you a flat list of sockets. Great for grepping, bad for *seeing structure*: which process owns a listener, which connections are loopback chatter between two local services, what a daemon actually talks to. socketscope turns that flat list into a force-directed graph you can search, filter, and trace through — so the shape of the system becomes obvious at a glance.

## Requirements

- **Python 3.6+** — standard library only, nothing to `pip install`. The viewer
  (`socketscope.py`) runs anywhere Python does.
- **Linux** for `sockets_graph.py` (it reads `/proc`); other generators have their own
  needs (`cmake_graph.py` wants `cmake` on PATH).
- A browser to open the result. The HTML is fully offline.

## Install

There's nothing to install — they're plain scripts with no dependencies. Copy the viewer
(`socketscope.py`) and whichever generators you want onto the host:

```bash
sudo python3 sockets_graph.py | python3 socketscope.py > sockets.html
```

Optionally make them executable (`chmod +x *.py`). Run `sockets_graph.py` with `sudo` for
full visibility (see below).

## Usage

A **generator** emits the JSON model to stdout; the **viewer** reads it (stdin or a file)
and writes the HTML:

```bash
sudo sockets_graph.py | socketscope.py > sockets.html       # sockets + processes
sudo sockets_graph.py --ignore-uds | socketscope.py -o net  # less noise -> net.html
sockets_graph.py | jq .                                     # the model is just JSON
dirtree_graph.py ~/project | socketscope.py > tree.html     # a directory tree
cmake_graph.py build       | socketscope.py > cmake.html     # CMake targets/deps
```

`socketscope.py` reads the model from **stdin** (default) or a **file argument**, and
writes HTML to **stdout** unless you pass `-o NAME` (→ `NAME.html`). It polls nothing and
needs no privileges — only the generator does. (`socketscope.py render -` is also accepted,
for symmetry with the old subcommand.) Save a generator's JSON to re-view or share later;
because the model fully determines the output, rendering the same model always produces the
same HTML.

**Run `sockets_graph.py` as root (`sudo`) for the full picture.** Unprivileged, the kernel
only lets you see the file descriptors of your *own* processes, so most sockets can't be
attributed to a process. It still works — it just shows less, and reports on stderr how
many sockets it couldn't attribute. It's a **snapshot** — re-run any time to refresh.

The generators print a one-line summary to **stderr**, keeping stdout clean for the pipe;
the viewer's "Download data (JSON)" button re-exports the embedded `{meta, node_classes,
edge_classes, style, edge_key, traversals, force_structures, nodes, edges}` model.

### Other generators (the model is the seam)

The viewer renders one generic JSON model, so **anything that emits that shape can be
visualized**. `sockets_graph.py` (above) is one such standalone generator; here are the
others that ship. They each build the model and pipe it to the viewer, importing nothing
from it — the JSON model is the only contract.

**`dirtree_graph.py`** — walk a directory into the model: nodes are directories, files,
and symlinks; edges are parent→child containment plus a **distinct dashed edge** from each
symlink to its target. Executable files get a green border; it ships **Descendants** /
**Path to root** traversals and a **directory skeleton** force structure, and each node
carries `size`/`mtime`/`ctime`/owner/`perms` in its tooltip.

```bash
dirtree_graph.py ~/project | socketscope.py render - > tree.html
dirtree_graph.py / --max-depth 3 | socketscope.py render -      # shallow, whole-system
dirtree_graph.py . --no-files  | socketscope.py render -        # directories only
```

Pass `-` as the path and it reads a newline-separated path list from **stdin** instead of
walking, synthesizing the ancestor directories needed to connect them — so filtering
(gitignore, etc.) is delegated to whatever upstream tool already knows which paths matter.
Relative entries resolve against **`-C`/`--directory`** (which also becomes the root) —
needed for `git ls-files`, whose paths are relative to the repo root:

```bash
git -C ~/p ls-files | dirtree_graph.py - -C ~/p | socketscope.py render -   # Git-tracked only
find . -name '*.py'  | dirtree_graph.py -        | socketscope.py render -
```

**`cmake_graph.py`** — read a CMake project's [File API](https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html)
and emit the target/dependency/source graph:

```bash
cmake_graph.py build | socketscope.py render - > cmake.html   # targets, deps, source files
cmake_graph.py build --no-sources | socketscope.py render -   # just the dependency DAG
```

Targets are colored by type (executable / static-library / …), edges are `link`
(target→dependency) and `source` (target→file); it's a real dependency **DAG**, so the
**Topo BFS** static layout and the *Depended on by* traversal (impact analysis) are the
natural tools. Source-file nodes start hidden — toggle the **source** node class on to
reveal them; CMake-internal `.rule`/generated stubs are split into a separate, also-hidden
**generated** class.

### Filtering at capture time

`sockets_graph.py --ignore` drops node classes from the data entirely (smaller file, less clutter). You can also just hide/show classes live in the viewer's legend after the fact. Class ids: `proc-root`, `proc-user`, `proc-kernel`, `tcp`, `udp`, `unix`, `unix-unnamed`, `remote`. Run `sockets_graph.py --help` for the convenience flags (`--ignore-uds`, `--ignore-kernel`, …).

## Exploring the graph

Each **node** is a process (blue = user, red = root, grey = kernel thread) or a socket (green TCP, gold UDP, purple UNIX) or a remote endpoint (pink). **Edges** are directed: process → its sockets → the peers/remotes they connect to, plus the process tree (grey "parent of" arrows). Listening sockets get a bold border, so service hubs stand out.

The graph self-organizes with a live force simulation that settles and stops. Then:

- **Search** — match nodes across all their text (command line, address, inode, type). Space-separated terms are AND'd; wrap in `/…/` for a regex (`/:(80|443)\b/`, `/sshd/i`). Matches become the selection.
- **Select** — generic topology tools that operate on the current selection: All / None / Invert, **Grow** (add neighbours), **Shrink** (erode — drop nodes touching the outside), **Walk** (step outward, drop the source), **Component** (whole connected group). Useful on *any* graph; no domain knowledge.
- **Trace chain** — the killer feature, and now a **data-driven traversal tool** (a `Traverse` button) rather than hardcoded. Select a process (or socket, or search result) and trace the connected **data chain**: it follows sockets *laterally* to other processes that share them and *down* to child processes — but never *up* to parents, so it won't climb to `init` and swallow the whole host. Its behavior is just a rule in the JSON (`{edge:"edge.tree",dir:"out"}, {edge:"edge.io",dir:"both"}`), so a graph can ship its own traversals (see Styling/Schema). Search `tcp`, hit Trace, and watch the related processes light up.
- **Pin** — freeze selected nodes in place (they still exert forces, so they anchor their neighbors). Pin a hub or a chain and let the rest settle around it.
- **Force structure** — how the layout's springs are weighted (a data-driven dropdown). socketscope ships **process tree** (cluster by ancestry) and **data flow** (cluster by socket connectivity); every graph also gets the built-in **spread** (all edges equal) and **distance from selected** (concentric rings of hop-distance). A **strength** slider scales the emphasis.
- **Filter** — two legends (**Node classes** and **Edge classes**) whose swatches show/hide by class. Nodes and edges each carry a *set* of classes (multi-membership), and visibility is **OR**: an element hides only when *all* its classes are off (so hiding the `file` edge class thins a dirtree to its directory skeleton, while an executable file stays visible via its `executable` class). **Kernel threads and UNIX-domain sockets start hidden** by default (the noisy bulk); which classes start hidden is data-driven (a `"hidden": true` flag on the catalog entry), not hardcoded. Classes not in the catalog collapse into an `other` row.
- **Pan/zoom** freely, **drag** nodes (they pin while held), **hover** for full details (cmdline, addresses, owners), click a node to isolate its neighbourhood.
- **Download data (JSON)** — export the captured graph model (nodes, edges, meta) for use elsewhere.

## A note on sharing the output

A sockets graph embeds a detailed picture of the host: process command lines (which can include arguments, paths, sometimes secrets), local and remote IP addresses, and UNIX socket paths. **Treat `sockets.html` like the sensitive snapshot it is** — it's git-ignored by default for that reason. Scrub or filter (`sockets_graph.py --ignore`) before sharing externally.

## How it works

`sockets_graph.py` builds the graph model:

1. Reads processes from `/proc/<pid>/{status,cmdline}` and the parent/child tree.
2. Parses sockets from `/proc/net/{tcp,tcp6,udp,udp6,unix}` (handling the little-endian address quirks itself — no dependency on `ss`/`lsof`).
3. Maps sockets to processes via `/proc/<pid>/fd/` (`socket:[inode]` links).
4. Emits the model as JSON. `socketscope.py` then embeds it in an HTML page whose viewer (Cytoscape.js, vendored inline) renders and explores it.

Cytoscape.js is bundled into the viewer as a compressed blob and decompressed at write time, so the output has **zero network references** and opens offline anywhere.

## Styling

Appearance is built from layered [Cytoscape stylesheets](https://js.cytoscape.org/#style), applied in order:

1. **Base** — baked into the viewer and strictly **domain-agnostic**: structure only (rectangles, labels-inside, sizing, arc edges + arrowheads, neutral greys). No class colors and no socketscope-specific fields. So *any* directed graph renders as readable labelled rectangles rather than bare dots.
2. **Class colors** — generated at runtime from `node_classes[]` / `edge_classes[]`: one rule per class (`node.tcp { background-color: … }`, `edge.io { line-color: … }`). The catalogs are therefore the **single source** for both the legend swatch *and* the element color, so they can't drift — recolor a class by editing its catalog entry and both update together. Each entry may carry `"hidden": true` to start that class unchecked. Because nodes/edges hold a **set** of classes, rules **compose** (a node that is both `file` and `executable` gets the `file` fill *and* the `executable` border); a class with no `color` is a pure modifier (e.g. `executable` contributes only its border). (Empty when a graph supplies no catalogs.)
3. **Snapshot `style`** — a top-level `style` array in the JSON (a Cytoscape stylesheet). A socketscope capture **prepopulates** this with its *domain* styling — the `node[listen = "yes"]` hub border and the `io`/`tree` edge colors — because those reference fields a generic graph wouldn't have. Edit it (or add your own) and `render` to restyle without touching code; a generic graph simply omits it.
4. **Interaction states** — selection, traced chain, pinned, faded — owned by the viewer and applied last, so a snapshot's `style` can restyle the graph but can't break selection/trace/pin.

A top-level **`edge_key`** (a list of plain-text lines) populates the viewer's "Edge style" key — domain text like `→ arrowhead = direction`. It's optional; a graph that omits it hides the section.

A top-level **`traversals`** array defines the **Traverse** tools (the buttons that grow the selection by rule). Each is `{id, label, mode:"flood"|"step", deselectSource?, recenter?, rules:[…]}`, and a rule is `{source?, edge?, target?, dir}` where each slot is a Cytoscape selector (omitted = match anything; slots AND, rules OR) and `dir` ∈ `out`/`in`/`both` relative to edge orientation. socketscope ships one tool — "Trace chain" (`tree` edges `out`, `io` edges `both`); any graph can define its own. The built-in **Select** tools (Grow/Shrink/Walk/Component/…) need no data and always work.

A top-level **`force_structures`** array defines the **Force structure** dropdown (how the layout weights its springs). Each is `{id, label, emphasize}` where `emphasize` is an edge selector; when active, matching edges spring strongly (strength-scaled) and the rest weakly, so the layout clusters around them. socketscope ships `tree`/`flow`; the viewer always adds built-in **spread** and **distance from selected**, so a graph that omits it still lays out.

Because the base is fully generic and `render` only requires `nodes` + `edges`, the viewer doubles as a renderer for **any directed graph** — hand a `{ "nodes": [...], "edges": [...] }` file (a tree, a dependency graph, …) to `socketscope.py render` and it draws. `node_classes`, `edge_classes`, `meta`, `style`, `edge_key`, `traversals`, and `force_structures` are all optional; nodes fall back to their `id` for a label, and any class not in a catalog shows up under the legend's `other` row.

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

socketscope sits in the gap between "static Graphviz dump of `ss`" and "stand up a whole observability platform" — a zero-install, single-host, **offline** exploration tool. Neighbours in the space:

**Interactive connection graphs (closest in spirit)**

- [Weave Scope](https://github.com/weaveworks/scope) — web UI graphing processes/containers/hosts and their connections from `/proc` + conntrack. The nearest analog, but it's an **agent + live server**, container/Kubernetes-oriented, and **no longer maintained** (Weaveworks shut down in 2024; last release 2021).
- [EtherApe](https://etherape.sourceforge.io/) — live graphical monitor where nodes are **hosts** and links are traffic, color-coded by protocol. It's a packet sniffer focused on live throughput, not process↔socket structure.

**Live per-process / per-connection monitors (lists, not graphs)**

- [bandwhich](https://github.com/imsnif/bandwhich), [nethogs](https://github.com/raboof/nethogs), `iftop`, `iptraf-ng`, `tcptrack` — terminal tools showing connections/bandwidth per process in real time. Great for "what's using the network *now*"; flat and throughput-focused.
- [grigio/network-monitor](https://github.com/grigio/network-monitor) — a recent (2025) Rust/GTK4 desktop GUI listing active connections with live I/O stats.

**The CLIs socketscope turns into a picture**

- `ss`, `lsof`, `netstat`, `pstree`, `procs` — the flat-list / text-tree tools it exists to make *visual*.

**Windows analogs**

- Sysinternals **TCPView** (process → endpoint mapping) + **Process Explorer** (process tree). socketscope is roughly "both, as one graph" for Linux.

**Cluster-scale / eBPF service maps**

- [Cilium Hubble](https://github.com/cilium/hubble), [Pixie](https://px.dev), Caretta, DeepFlow — auto service-connectivity graphs, usually eBPF-based and Kubernetes-scoped. Far more powerful for distributed flows, but they need real infrastructure and work at the service level, not "every socket and the process holding it on one box."

**How socketscope differs:** a single self-contained **offline HTML file** (no agent, no server, no install); a **whole-host `/proc` snapshot** covering TCP/UDP **and** UNIX-domain sockets **plus** the process tree in one view; and an **exploration-first** UI (trace-chain data-flow walk, focus modes, pin, search).

## License

socketscope is released under the [MIT License](LICENSE). It bundles [Cytoscape.js](https://js.cytoscape.org/) (also MIT), whose attribution is preserved inside the script.
