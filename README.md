# socketscope

**See every open socket on a Linux host and the processes behind them — as one interactive, offline graph.**

`socketscope` takes a point-in-time snapshot of every socket on a machine (TCP, UDP, UNIX-domain) and the processes using them, reads the process tree, and writes a **single self-contained HTML file**. Open it in any browser — no server, no internet, no install — and explore who's listening, who's connected to whom, and how data flows between processes.

It's one Python script with **zero dependencies** (standard library only). The visualization library is baked into the script, so the HTML it produces works completely offline.

```bash
sudo python3 socketscope.py            # writes socketscope-<timestamp>.html
# then open that file in your browser
```

---

## Why

`ss`, `lsof`, and `netstat` give you a flat list of sockets. Great for grepping, bad for *seeing structure*: which process owns a listener, which connections are loopback chatter between two local services, what a daemon actually talks to. socketscope turns that flat list into a force-directed graph you can search, filter, and trace through — so the shape of the system becomes obvious at a glance.

## Requirements

- **Linux** (it reads `/proc`).
- **Python 3.6+** — standard library only, nothing to `pip install`.
- A browser to open the result. The HTML is fully offline.

## Install

There's nothing to install — it's one file with no dependencies. Copy `socketscope.py` onto the host and run it:

```bash
python3 socketscope.py
```

Optionally make it executable (`chmod +x socketscope.py` → `./socketscope.py`). Run with `sudo` for full visibility (see below).

## Usage

```bash
sudo python3 socketscope.py                          # -> socketscope-<timestamp>.html
sudo python3 socketscope.py --json                   # also write the .json model
sudo python3 socketscope.py --json --no-html -o - | jq .   # stream JSON to a pipe
socketscope.py --ignore-uds -o net                   # unprivileged -> net.html
```

**Run as root (`sudo`) for the full picture.** Unprivileged, the kernel only lets you see the file descriptors of your *own* processes, so most sockets can't be attributed to a process. socketscope still works — it just shows less, and prints a hint to re-run with `sudo`. The capture summary always reports how many sockets it couldn't attribute.

It's a **snapshot** — re-run it any time to refresh.

### Output

By default socketscope writes one file, **`socketscope-<timestamp>.html`**, so repeated runs don't overwrite each other. `-o NAME` sets the base name and the `.html`/`.json` extension is appended for you (a name you type *with* an extension is accepted too). Add **`--json`** to also write the raw graph model as `<base>.json`, **`--no-html`** to skip the viewer, and **`-o -`** to stream a single artifact to stdout — so `socketscope.py --json --no-html -o - | jq` works for scripting. The human-readable capture summary always goes to **stderr**, keeping stdout clean for piping. The JSON is the same `{meta, types, nodes, edges}` model the viewer's "Download data" button produces.

### Rendering a saved snapshot

socketscope is really two steps — **snapshot** the system into a JSON model, then **render** that model into HTML — and the default run does both. The **`render`** subcommand runs just the second step: it turns a saved snapshot JSON back into the HTML viewer **without polling the system at all**. Use it to re-view an archived capture, render a snapshot taken on another host, or rebuild the HTML from a capture piped in.

```bash
socketscope.py render snap.json                 # -> HTML on stdout
socketscope.py render snap.json -o view         # -> view.html
socketscope.py render snap.json > view.html     # same, via redirect
socketscope.py --json --no-html -o - | socketscope.py render   # capture | render
```

`render` is a plain filter: it reads the snapshot from a **file argument** or, if omitted (or given `-`), from **stdin**, and writes HTML to **stdout** unless you pass `-o NAME` (→ `NAME.html`). It polls nothing, so it needs no privileges; the rendered HTML reflects the snapshot's *original* host and capture time. Because the model fully determines the output, `render` of a capture's `.json` reproduces that capture's `.html` exactly.

### Filtering at capture time

`--ignore` drops node types from the data entirely (smaller file, less clutter). You can also just hide/show types live in the viewer's legend after the fact. Type ids: `proc-root`, `proc-user`, `proc-kernel`, `tcp`, `udp`, `unix`, `unix-unnamed`, `remote`. Run `socketscope.py --help` for the convenience flags (`--ignore-uds`, `--ignore-kernel`, …).

## Exploring the graph

Each **node** is a process (blue = user, red = root, grey = kernel thread) or a socket (green TCP, gold UDP, purple UNIX) or a remote endpoint (pink). **Edges** are directed: process → its sockets → the peers/remotes they connect to, plus the process tree (grey "parent of" arrows). Listening sockets get a bold border, so service hubs stand out.

The graph self-organizes with a live force simulation that settles and stops. Then:

- **Search** — match nodes across all their text (command line, address, inode, type). Space-separated terms are AND'd; wrap in `/…/` for a regex (`/:(80|443)\b/`, `/sshd/i`). Matches become the selection.
- **Trace chain** — the killer feature. Select a process (or a socket, or a search result) and trace the connected **data chain**: it follows sockets *laterally* to other processes that share them and *down* to child processes — but never *up* to parents, so it won't climb to `init` and swallow the whole host. Search `tcp`, hit Trace, and watch the related processes light up.
- **Pin** — freeze selected nodes in place (they still exert forces, so they anchor their neighbors). Pin a hub or a chain and let the rest settle around it.
- **Focus** — what the layout optimizes for: **process tree** (cluster by ancestry), **data flow** (cluster by socket connectivity), or **distance from selected** (concentric rings of hop-distance). A **strength** slider scales it.
- **Filter** — click legend swatches to show/hide node types. **Kernel threads and UNIX-domain sockets start hidden** by default (they're the noisy bulk).
- **Pan/zoom** freely, **drag** nodes (they pin while held), **hover** for full details (cmdline, addresses, owners), click a node to isolate its neighbourhood.
- **Download data (JSON)** — export the captured graph model (nodes, edges, meta) for use elsewhere.

## A note on sharing the output

The generated HTML embeds a detailed picture of the host: process command lines (which can include arguments, paths, sometimes secrets), local and remote IP addresses, and UNIX socket paths. **Treat `sockets.html` like the sensitive snapshot it is** — it's git-ignored by default for that reason. Scrub or filter (`--ignore`) before sharing externally.

## How it works

1. Reads processes from `/proc/<pid>/{status,cmdline}` and the parent/child tree.
2. Parses sockets from `/proc/net/{tcp,tcp6,udp,udp6,unix}` (handling the little-endian address quirks itself — no dependency on `ss`/`lsof`).
3. Maps sockets to processes via `/proc/<pid>/fd/` (`socket:[inode]` links).
4. Builds a graph model and emits it as JSON inside an HTML page whose viewer (Cytoscape.js, vendored inline) renders and explores it.

Cytoscape.js is bundled into the script as a compressed blob and decompressed at write time, so the output has **zero network references** and opens offline anywhere.

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
