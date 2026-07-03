# gdvb

**Turn anything with structure — a running system, a codebase, a filesystem — into an interactive, offline graph you can explore in a browser.**

gdvb is two things: small **generator** scripts that snapshot something into a generic JSON graph model, and **`gdvb-render`**, one domain-agnostic **viewer** that turns any such model into a single self-contained HTML file. Open it anywhere — no server, no internet, no install.

The most useful generator today is **`gdvb-sockets-graph`**: it captures every open socket on a Linux host (TCP/UDP/UNIX), the processes behind them, and the process tree, so you can *see* who's listening, who's connected to whom, and how data actually flows — something `ss`/`lsof`/`netstat` can't show you, since they only give you a flat list. But sockets are just one generator; the JSON model is a generic typed directed graph, so anything that emits that shape gets the same viewer for free — a directory tree, a build's dependency DAG, a codebase's call graph all ship today.

```bash
sudo ./gdvb-sockets-graph | ./gdvb-render > sockets.html
# open sockets.html in a browser
```

## How it works

A **generator** does one job: read *something* (a filesystem, a build directory, a running process's `/proc`, a language server) and print a JSON graph model to stdout. The **viewer**, `gdvb-render`, does the other: read that JSON (stdin or a file) and write one offline HTML page. Neither imports the other — the JSON model is the only contract between them ("the model is the seam"), so writing a new generator is just emitting that shape, and the viewer never needs to know what domain it's rendering.

The viewer is built on [Cytoscape.js](https://js.cytoscape.org/) (a graph layout/rendering library), vendored inline as a compressed blob and decompressed at write time — so the HTML it produces has zero network references and opens completely offline, in any modern browser.

## Install

There's nothing to install — copy `gdvb-render` and whichever generator(s) you want onto the machine, or clone the repo, and run. On the Python side it's genuinely **zero dependencies** (standard library only, nothing to `pip install`); beyond that, each generator needs whatever it's reading to actually exist on the machine — not an extra dependency you install *for* gdvb, just the subject matter itself:

- **Python 3.6+** for everything.
- **Linux** for `gdvb-sockets-graph` specifically (it reads `/proc`).
- **`cmake` on `PATH`** for `gdvb-cmake-graph`.
- **A language server installed** (`clangd`, `pyright`) for the `gdvb-*-lsp-graph` wrappers.
- **A browser** to open the result — a modern evergreen one (~2019+); nothing loads over the network, so this works air-gapped.

## Usage

```bash
sudo ./gdvb-sockets-graph | ./gdvb-render > sockets.html    # sockets + processes
./gdvb-dirtree-graph ~/project | ./gdvb-render > tree.html  # a directory tree
./gdvb-cmake-graph build | ./gdvb-render > cmake.html       # CMake targets/deps
./gdvb-clangd-lsp-graph proj --seed main | ./gdvb-render    # a C/C++ call graph
./gdvb-pyright-lsp-graph proj --all | ./gdvb-render         # a whole Python project
```

Every generator prints JSON to stdout (and a one-line summary to stderr, so stdout stays clean for the pipe) and takes its own flags — run any of them with `--help`. `gdvb-render` reads the model from stdin or a file argument and writes HTML to stdout, or to `NAME.html` with `-o NAME`; it polls nothing and needs no privileges (only some generators do — e.g. run `gdvb-sockets-graph` as root for full process↔socket attribution).

A generator's JSON model fully determines the output, so you can save it and re-render later, or hand it to someone else:

```bash
sudo ./gdvb-sockets-graph > snapshot.json
./gdvb-render snapshot.json > sockets.html   # same model -> same HTML, any time
```

`just bundle <generator>` fuses a generator and the viewer into one self-contained runnable script (`dist/gdvb-{subject}`) — capture and render in a single invocation, nothing to pipe:

```bash
just bundle gdvb-sockets-graph           # -> dist/gdvb-sockets
sudo ./dist/gdvb-sockets -o sockets.html
```

**Sharing output**: a sockets capture embeds a detailed picture of the host (command lines, IPs, socket paths) — treat it as sensitive. Filter at capture time (`gdvb-sockets-graph --ignore-uds`, etc.) and/or run it through **`gdvb-scrub`** before sharing, a filter that redacts host-identifying data (ids, IPs, hostname, usernames, pids, cmdline args, UNIX paths — nine independently-disableable ops; `gdvb-scrub --help` for the full list):

```bash
./gdvb-sockets-graph | ./gdvb-scrub | ./gdvb-render > safe.html
```

## Exploring the graph

Once open, a graph self-organizes with a live force simulation, then:

- **Search** — match any node's text (command line, address, filename, ...); wrap in `/…/` for regex. Matches become the selection.
- **Select** — generic topology tools on the current selection: Grow (add neighbours), Shrink, Walk, Component. Work on any graph, no domain knowledge needed.
- **Traverse** — data-driven, graph-specific tools (e.g. sockets' "Trace chain" follows a process's data flow; a codebase's "Callers"/"Callees" walk its call graph).
- **Pin** — freeze selected nodes in the live force layout (they still exert forces, anchoring their neighbors).
- **Mark** — flag nodes as a static layout's root/anchor, independent of Pin.
- **Static layouts** (Topo BFS, Undirected BFS) — lay the graph out by hop-distance instead of physics.
- **Force structure** — how the live layout's springs are weighted (e.g. cluster by process tree vs. data flow); every graph also gets built-in "spread" and "distance from selected".
- **Filter** — two legends (node/edge classes) toggle visibility; classes compose, so an element hides only when *all* its classes are off.
- **Download data (JSON)** — re-export the graph model.

A graph is a **snapshot**, not a live monitor — re-run the generator to refresh. `gdvb-sockets-graph` specifically only sees its own network namespace, and can't link the two ends of a UNIX socket pair (a `/proc` limitation, not a bug). On a **big-endian** host (e.g. s390x), IP address *text* renders wrong, though the graph structure and ports are still correct — everything else assumes little-endian, which is effectively every common Linux machine.

## Extending gdvb

- **The model is the seam.** A generator's whole contract is the JSON shape `{meta, node_classes, edge_classes, style, edge_key, traversals, force_structures, nodes, edges}` — only `nodes`/`edges` are required, so `gdvb-render` doubles as a viewer for *any* directed graph (`{"nodes":[...],"edges":[...]}`), and a new generator needs zero knowledge of the viewer's internals.
- **Styling is layered**: a domain-agnostic base (baked into the viewer) + generated per-class colors (from `node_classes`/`edge_classes` — the single source for both the legend swatch and the element color) + an optional snapshot `style` (a raw [Cytoscape stylesheet](https://js.cytoscape.org/#style)) + viewer-owned interaction states (selection, pin, trace), applied in that order.
- **Generator conventions (C1–C4)**, required for a generator to be pipeable and bundleable: a top-level `main()` that writes the model JSON to stdout and returns on success (C1); no `-o`/`--out` flag, reserved for the bundle's HTML output (C2); no top-level name `Viewer` (C3); errors via `SystemExit` (C4). `just bundle` lints these and refuses a generator that violates them.
- **Naming**: lowercase kebab-case, no `.py` extension. Generators are `{subject}-graph`; the viewer is `gdvb-render`. `gdvb-scrub` (a filter, not a generator) and `gdvb-lsp-graph` (a shared LSP client, see below) are the two scripts that don't fit that pattern.
- **`gdvb-lsp-graph` is a client, not a generator.** LSP only specifies the JSON-RPC protocol, not a transport or how to launch a server with the right flags — so `gdvb-lsp-graph` never spawns one; it just connects to a socket (`--connect`). `gdvb-clangd-lsp-graph`/`gdvb-pyright-lsp-graph` are the actual generators: each spawns its server, bridges its stdio to a fresh Unix domain socket, and calls `gdvb-lsp-graph --connect` pointed at it. Adding a new language/server is a third small wrapper in this same shape.
- **Bundling mechanics**: `just bundle` cats the viewer (all under one `class Viewer`) + the generator + a small glue tail (`bundle_main.py`) into one file. At runtime the glue calls the generator's `main()`, captures the model JSON it writes to stdout, and hands it to `Viewer.emit_html` — so a bundle accepts all of the generator's own flags plus a bundle-provided `-o NAME`.
- **No external tools, nothing new.** Reads `/proc` directly (no `ss`/`lsof` dependency); uses only long-stable `/proc` interfaces (no eBPF, no cgroup v2); Python 3.6+ stdlib only.

## License

gdvb is released under the [MIT License](LICENSE). It bundles [Cytoscape.js](https://js.cytoscape.org/) (also MIT), whose attribution is preserved inside the script.
