#!/usr/bin/env python3
"""sockets_graph - emit the open sockets + processes graph as JSON.

A standalone generator for the socketscope viewer. It snapshots every open
socket and the processes using them straight from /proc, then prints ONE JSON
graph model to stdout - the same generic model dirtree_graph.py / cmake_graph.py
produce. It does NOT import render-graph-html.py; the JSON model is the only contract.
Pipe it to the viewer:

    sudo sockets_graph.py | render-graph-html.py > sockets.html

Run as root (sudo) to attribute system-owned sockets to their processes;
unprivileged it sees only your own processes' descriptors. Stdlib only; Linux.
"""
import os
import sys
import pwd
import json
import socket
import argparse
import datetime


# ---------------------------------------------------------------------------
# Class catalogs (drive color / filter / legend). Nodes and edges each carry a
# set of classes (multi-membership, like CSS); these catalogs describe each
# class: color, legend label, and default visibility. An element whose class
# isn't cataloged falls into the viewer's synthesized "other" legend bucket.
# ---------------------------------------------------------------------------
NODE_CLASSES = [
    {"id": "proc-root", "label": "Process (root)", "color": "#E0533F"},
    {"id": "proc-user", "label": "Process (user)", "color": "#3F8EE0"},
    # `hidden`: starts unchecked in the viewer's filter (the noisy bulk).
    # Absent => shown. The viewer reads this, so the default is data-driven.
    {"id": "proc-kernel", "label": "Kernel thread", "color": "#9AA0A6", "hidden": True},
    {"id": "tcp", "label": "TCP socket", "color": "#2FA86E"},
    {"id": "udp", "label": "UDP socket", "color": "#C9A227"},
    {"id": "unix", "label": "UNIX socket (named)", "color": "#8A63D2", "hidden": True},
    {
        "id": "unix-unnamed",
        "label": "UNIX socket (unnamed)",
        "color": "#B9A3E3",
        "hidden": True,
    },
    {"id": "remote", "label": "Remote endpoint", "color": "#D46BB0"},
]

# Edge classes. `io` has no catalog color on purpose: DOMAIN_STYLE recolors io
# edges per source node (data(col)), so io has no single color — declaring one
# would only mislead the legend swatch. A catalog color means "renders in this
# color"; classes recolored by `style` (or with no fixed color) omit it.
EDGE_CLASSES = [
    {"id": "tree", "label": "process tree", "color": "#c3c8d0"},
    {"id": "io", "label": "I/O (socket)"},
]

# Domain-specific appearance, emitted as the model's `style` block. These rules
# reference socketscope's own node/edge fields (`listen`, the `tree`/`io` edge
# classes), which a generic directed graph won't have — so they live here in the
# data, not in the viewer's domain-agnostic baked-in base style. A graph that
# carries no `style` (e.g. a hand-made tree) simply skips them. The viewer layers:
# base (generic) + per-class colors (from node_classes/edge_classes) + this
# `style` + interaction.
DOMAIN_STYLE = [
    {
        "selector": 'node[listen = "yes"]',
        "style": {"border-width": 3, "border-color": "#333"},
    },
    {
        "selector": "edge.io",
        "style": {"line-color": "data(col)", "target-arrow-color": "data(col)"},
    },
    {
        "selector": "edge.tree",
        "style": {
            "line-color": "#c3c8d0",
            "target-arrow-color": "#c3c8d0",
            "width": 1,
        },
    },
    {
        "selector": "edge.tree.showlabel",
        "style": {"color": "#9aa0a6", "font-style": "italic", "font-size": 8},
    },
]

# Human-readable key for the edge styling, emitted as the model's top-level
# `edge_key` and shown under "Edge style" in the viewer. Domain-specific text, so
# it lives in the data; a generic graph that omits it hides the section.
EDGE_KEY = [
    "→ arrowhead = direction",
    "colored arc = I/O relationship",
    "grey italic = process tree",
]

# Data-driven traversal tools, emitted as the model's top-level `traversals` and
# shown as buttons under "Traverse" in the viewer. Each tool grows the selection
# along edges matching its rules. A rule's `edge`/`source`/`target` are Cytoscape
# selectors (the same language as `style`), all optional and AND-ed; multiple
# rules OR. `dir` is relative to edge orientation: out = source->target,
# in = target->source, both = either. This is the old hardcoded "Trace chain"
# expressed as data: follow the process tree DOWN (tree edges, source->target
# only) and sockets BOTH ways, so a flood never climbs to init. Generic graphs
# omit this; the viewer's built-in Select tools still work.
TRAVERSALS = [
    {
        "id": "trace",
        "label": "🔗 Trace chain",
        "mode": "flood",
        "rules": [
            {"edge": "edge.tree", "dir": "out"},
            {"edge": "edge.io", "dir": "both"},
        ],
    },
]

# Force-layout structures ("Force Structure" selector), emitted as the model's
# top-level `force_structures`. Each mode makes edges matching its `emphasize`
# selector spring strongly (strength-scaled) and the rest weak — so the layout
# clusters around those edges. `emphasize` is a Cytoscape edge selector (same
# language as `style`). The viewer also offers built-in generic modes (spread =
# all edges equal; distance-from-selected = radial rings), so a graph that omits
# this still lays out.
FORCE_STRUCTURES = [
    {"id": "tree", "label": "process tree", "emphasize": "edge.tree"},
    {"id": "flow", "label": "data flow", "emphasize": "edge.io"},
]

TCP_STATES = {
    0x01: "ESTABLISHED",
    0x02: "SYN_SENT",
    0x03: "SYN_RECV",
    0x04: "FIN_WAIT1",
    0x05: "FIN_WAIT2",
    0x06: "TIME_WAIT",
    0x07: "CLOSE",
    0x08: "CLOSE_WAIT",
    0x09: "LAST_ACK",
    0x0A: "LISTEN",
    0x0B: "CLOSING",
    0x0C: "NEW_SYN_RECV",
}


# ---------------------------------------------------------------------------
# A1. Processes
# ---------------------------------------------------------------------------
def read_processes():
    procs = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        base = "/proc/%d" % pid
        try:
            with open(base + "/status", "r") as fh:
                status = fh.read()
        except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
            continue
        name = ppid = uid = state = None
        for line in status.splitlines():
            if line.startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("PPid:"):
                try:
                    ppid = int(line.split(":", 1)[1].strip())
                except ValueError:
                    ppid = 0
            elif line.startswith("Uid:"):
                try:
                    uid = int(line.split(":", 1)[1].split()[0])
                except (ValueError, IndexError):
                    uid = None
            elif line.startswith("State:"):
                state = line.split(":", 1)[1].strip()
        # cmdline -> NUL-separated argv; empty => kernel thread
        cmdline = ""
        try:
            with open(base + "/cmdline", "rb") as fh:
                raw = fh.read()
            argv = [a.decode("utf-8", "replace") for a in raw.split(b"\x00") if a]
            cmdline = " ".join(argv)
        except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
            cmdline = ""
        is_kernel_thread = cmdline == ""
        if not cmdline:
            cmdline = "[%s]" % (name or "?")
        try:
            user = pwd.getpwuid(uid).pw_name if uid is not None else "?"
        except (KeyError, TypeError):
            user = str(uid)
        procs[pid] = {
            "pid": pid,
            "comm": name or "?",
            "cmdline": cmdline,
            "uid": uid if uid is not None else -1,
            "user": user,
            "ppid": ppid if ppid is not None else 0,
            "is_kernel_thread": is_kernel_thread,
            "state": state or "?",
        }
    return procs


# ---------------------------------------------------------------------------
# A2. Sockets - address parsing
# ---------------------------------------------------------------------------
def _ipv4(hex_field):
    """'0100007F:0050' -> ('127.0.0.1', 80). IP is little-endian, port big."""
    ip_hex, port_hex = hex_field.split(":")
    ip = socket.inet_ntoa(bytes.fromhex(ip_hex)[::-1])
    return ip, int(port_hex, 16)


def _ipv6(hex_field):
    """32 hex chars = 4 little-endian 32-bit words -> IPv6 string."""
    ip_hex, port_hex = hex_field.split(":")
    b = bytes.fromhex(ip_hex)
    raw = b"".join(b[i : i + 4][::-1] for i in range(0, 16, 4))
    ip = socket.inet_ntop(socket.AF_INET6, raw)
    # collapse v4-mapped ::ffff:a.b.c.d already handled by inet_ntop
    return ip, int(port_hex, 16)


def _fmt(ip, port):
    if ":" in ip:  # IPv6 -> bracket
        return "[%s]:%d" % (ip, port)
    return "%s:%d" % (ip, port)


def parse_inet(path, family):
    """Parse /proc/net/{tcp,tcp6,udp,udp6}."""
    out = []
    try:
        with open(path, "r") as fh:
            lines = fh.read().splitlines()
    except (PermissionError, FileNotFoundError, OSError):
        return out
    is6 = family.endswith("6")
    is_udp = family.startswith("udp")
    base_fam = "udp" if is_udp else "tcp"
    for line in lines[1:]:
        f = line.split()
        if len(f) < 10:
            continue
        try:
            st = int(f[3], 16)
            inode = f[9]
            if is6:
                lip, lport = _ipv6(f[1])
                rip, rport = _ipv6(f[2])
            else:
                lip, lport = _ipv4(f[1])
                rip, rport = _ipv4(f[2])
        except (ValueError, IndexError, OSError):
            continue
        if inode == "0":  # TIME_WAIT / request socks: no fd, not attributable
            continue
        if is_udp:
            listening = False
            state = "BOUND"
        else:
            listening = st == 0x0A
            state = TCP_STATES.get(st, "0x%02X" % st)
        has_peer = rport != 0 and rip not in ("0.0.0.0", "::")
        out.append(
            {
                "inode": inode,
                "family": family,
                "base": base_fam,
                "kind": "dgram" if is_udp else "stream",
                "state": state,
                "local": _fmt(lip, lport),
                "peer": _fmt(rip, rport) if has_peer else "",
                "lip": lip,
                "lport": lport,
                "rip": rip,
                "rport": rport,
                "listening": listening,
            }
        )
    return out


def parse_unix(path="/proc/net/unix"):
    out = []
    try:
        with open(path, "r") as fh:
            lines = fh.read().splitlines()
    except (PermissionError, FileNotFoundError, OSError):
        return out
    kinds = {0x0001: "stream", 0x0002: "dgram", 0x0005: "seqpacket"}
    for line in lines[1:]:
        parts = line.split(None, 7)
        if len(parts) < 7:
            continue
        try:
            flags = int(parts[3], 16)
            typ = int(parts[4], 16)
            st = int(parts[5], 16)
        except ValueError:
            continue
        inode = parts[6]
        if inode == "0":
            continue
        p = parts[7] if len(parts) > 7 else ""
        # Named (has a path, incl. abstract "@...") vs unnamed get distinct
        # node types so they can be filtered independently.
        base = "unix" if p else "unix-unnamed"
        out.append(
            {
                "inode": inode,
                "family": "unix",
                "base": base,
                "kind": kinds.get(typ, "stream"),
                "state": "CONNECTED" if st == 0x03 else "UNCONNECTED",
                "local": p,
                "peer": "",
                "lip": "",
                "lport": 0,
                "rip": "",
                "rport": 0,
                "listening": bool(flags & 0x10000),  # SO_ACCEPTCON
            }
        )
    return out


def read_sockets():
    socks = []
    socks += parse_inet("/proc/net/tcp", "tcp")
    socks += parse_inet("/proc/net/tcp6", "tcp6")
    socks += parse_inet("/proc/net/udp", "udp")
    socks += parse_inet("/proc/net/udp6", "udp6")
    socks += parse_unix("/proc/net/unix")
    # de-dup by inode (a v4 socket can also appear via other paths); first wins
    seen, uniq = set(), []
    for s in socks:
        if s["inode"] in seen:
            continue
        seen.add(s["inode"])
        uniq.append(s)
    return uniq


# ---------------------------------------------------------------------------
# A3. inode -> pids, from /proc/<pid>/fd
# ---------------------------------------------------------------------------
def map_inode_pids(pids):
    inode2pids = {}
    for pid in pids:
        fddir = "/proc/%d/fd" % pid
        try:
            entries = os.listdir(fddir)
        except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
            continue
        for e in entries:
            try:
                target = os.readlink(os.path.join(fddir, e))
            except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
                continue
            if target.startswith("socket:["):
                ino = target[len("socket:[") : -1]
                inode2pids.setdefault(ino, set()).add(pid)
    return inode2pids


# ---------------------------------------------------------------------------
# A4. Build the graph model
# ---------------------------------------------------------------------------
def _short(s, n=42):
    return s if len(s) <= n else s[: n - 1] + "…"


def proc_label(p):
    return _short("%s (%d)" % (p["comm"], p["pid"]), 26)


def proc_full(p, nsock):
    return "%s\ncmd: %s\nuser: %s (uid %d)   ppid: %d\nstate: %s   sockets: %d" % (
        p["comm"],
        _short(p["cmdline"], 200),
        p["user"],
        p["uid"],
        p["ppid"],
        p["state"],
        nsock,
    )


def sock_label(s):
    if s["family"] == "unix":
        path = s["local"]
        if not path:
            return "unix:%s" % s["kind"]  # unnamed
        if path.startswith("@"):
            return "@" + os.path.basename(path[1:] or path)
        return _short(os.path.basename(path) or path, 28)
    if s["listening"]:
        return "%s :%d LISTEN" % (s["base"], s["lport"])
    return _short("%s %s" % (s["base"], s["local"]), 28)


def sock_full(s, pids):
    owners = ",".join(str(p) for p in sorted(pids)) if pids else "(none)"
    return "%s/%s\nlocal: %s\npeer:  %s\nstate: %s   inode: %s\nowners: %s" % (
        s["family"],
        s["kind"],
        s["local"] or "(unnamed)",
        s["peer"] or "-",
        s["state"],
        s["inode"],
        owners,
    )


def build_graph(procs, socks, inode2pids, is_root, ignore=None, captured=None):
    ignore = ignore or set()
    nodes, edges = [], []
    node_ids = set()

    def add_node(nid, label, full, ntype, listen=False):
        if ntype in ignore or nid in node_ids:
            return
        node_ids.add(nid)
        nodes.append(
            {
                "id": nid,
                "label": label,
                "full": full,
                "classes": [ntype],
                "listen": bool(listen),
            }
        )

    # processes
    for pid, p in procs.items():
        if p["is_kernel_thread"]:
            ntype = "proc-kernel"
        elif p["uid"] == 0:
            ntype = "proc-root"
        else:
            ntype = "proc-user"
        nsock = sum(1 for s in socks if pid in inode2pids.get(s["inode"], ()))
        add_node("p:%d" % pid, proc_label(p), proc_full(p, nsock), ntype)

    # sockets
    local_index = {}  # (ip,port) -> inode, for loopback peer matching (tcp)
    for s in socks:
        pids = inode2pids.get(s["inode"], set())
        add_node(
            "s:%s" % s["inode"],
            sock_label(s),
            sock_full(s, pids),
            s["base"],
            listen=s["listening"],
        )
        if s["base"] == "tcp" and s["lport"]:
            local_index.setdefault((s["lip"], s["lport"]), s["inode"])

    # tree edges: parent -> child
    for pid, p in procs.items():
        ppid = p["ppid"]
        if ppid and ppid in procs and ppid != pid:
            edges.append(
                {
                    "source": "p:%d" % ppid,
                    "target": "p:%d" % pid,
                    "label": "parent of",
                    "classes": ["tree"],
                }
            )

    # io edges: process -> socket
    for s in socks:
        sid = "s:%s" % s["inode"]
        for pid in inode2pids.get(s["inode"], ()):
            edges.append(
                {
                    "source": "p:%d" % pid,
                    "target": sid,
                    "label": _io_label(s),
                    "classes": ["io"],
                }
            )

    # io edges: socket -> remote (or peer for loopback tcp)
    peer_seen = set()
    for s in socks:
        if s["base"] in ignore:
            continue
        if s["base"] != "tcp" or s["state"] != "ESTABLISHED" or not s["peer"]:
            continue
        sid = "s:%s" % s["inode"]
        peer_key = (s["rip"], s["rport"])
        peer_inode = local_index.get(peer_key)
        if peer_inode and peer_inode != s["inode"]:
            # loopback: link the two local sockets once
            pair = tuple(sorted((s["inode"], peer_inode)))
            if pair not in peer_seen:
                peer_seen.add(pair)
                edges.append(
                    {
                        "source": sid,
                        "target": "s:%s" % peer_inode,
                        "label": "peer",
                        "classes": ["io"],
                    }
                )
        else:
            rid = "r:%s" % s["peer"]
            add_node(
                rid, _short(s["peer"], 30), "remote endpoint\n%s" % s["peer"], "remote"
            )
            edges.append(
                {
                    "source": sid,
                    "target": rid,
                    "label": "connects",
                    "classes": ["io"],
                }
            )

    # drop edges whose endpoints aren't both present
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    # unattributed sockets (real inode, no owning pid), among kept socket types
    unattributed = sum(
        1 for s in socks if s["base"] not in ignore and not inode2pids.get(s["inode"])
    )

    counts = {
        "nodes": len(nodes),
        "edges": len(edges),
        "by_type": {},
        "by_class": {},
        "unattributed": unattributed,
    }
    for n in nodes:
        for c in n["classes"]:
            counts["by_type"][c] = counts["by_type"].get(c, 0) + 1
    for e in edges:
        for c in e["classes"]:
            counts["by_class"][c] = counts["by_class"].get(c, 0) + 1

    node_classes = [c for c in NODE_CLASSES if c["id"] not in ignore]
    captured = captured or datetime.datetime.now().astimezone()
    # title/subtitle are viewer presentation hints (tab title, header chip), kept
    # in the data so the viewer hardcodes no socket-specific wording.
    meta = {
        "title": "sockets — " + socket.gethostname(),
        "subtitle": (
            "root — full visibility" if is_root else "unprivileged — own processes only"
        ),
        "host": socket.gethostname(),
        "captured": captured.isoformat(timespec="seconds"),
        "root": is_root,
        "ignored": sorted(ignore),
        "counts": counts,
    }
    return (
        {
            "meta": meta,
            "node_classes": node_classes,
            "edge_classes": EDGE_CLASSES,
            "style": DOMAIN_STYLE,
            "edge_key": EDGE_KEY,
            "traversals": TRAVERSALS,
            "force_structures": FORCE_STRUCTURES,
            "nodes": nodes,
            "edges": edges,
        },
        unattributed,
    )


def _io_label(s):
    if s["listening"]:
        return "listen"
    st = s["state"]
    if st == "ESTABLISHED":
        return "established"
    if st == "CONNECTED":
        return "connected"
    if s["base"] == "udp":
        return "udp"
    if st in ("BOUND", "UNCONNECTED"):
        return "bound"
    return st.lower() if st else "fd"


def main():
    type_ids = [c["id"] for c in NODE_CLASSES]
    ap = argparse.ArgumentParser(
        prog="sockets_graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Snapshot every open socket and the processes using them from /proc\n"
            "and emit a graph model JSON for the socketscope viewer. Pipe to:\n"
            "render-graph-html.py\n"
            "Run as root (sudo) to attribute system-owned sockets to processes."
        ),
        epilog=(
            "examples:\n"
            "  sudo sockets_graph.py | render-graph-html.py > sockets.html\n"
            "  sudo sockets_graph.py --ignore-uds | render-graph-html.py\n"
            "\n"
            "node class ids (for --ignore): " + ", ".join(type_ids)
        ),
    )
    g = ap.add_argument_group("filtering (exclude node classes from the graph)")
    g.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="CLASS",
        help="exclude class(es); repeatable or comma-separated, "
        "e.g. --ignore unix-unnamed,udp",
    )
    g.add_argument(
        "--ignore-uds",
        action="store_true",
        help="exclude all UNIX-domain sockets (named + unnamed)",
    )
    g.add_argument(
        "--ignore-uds-unnamed",
        action="store_true",
        help="exclude only unnamed UNIX-domain sockets (the noisy ones)",
    )
    g.add_argument("--ignore-tcp", action="store_true", help="exclude TCP sockets")
    g.add_argument("--ignore-udp", action="store_true", help="exclude UDP sockets")
    g.add_argument(
        "--ignore-remote",
        action="store_true",
        help="exclude remote (foreign) endpoints",
    )
    g.add_argument(
        "--ignore-kernel", action="store_true", help="exclude kernel threads"
    )
    args = ap.parse_args()

    ignore = set()
    for item in args.ignore:
        ignore.update(x.strip() for x in item.split(",") if x.strip())
    if args.ignore_uds:
        ignore.update({"unix", "unix-unnamed"})
    if args.ignore_uds_unnamed:
        ignore.add("unix-unnamed")
    if args.ignore_tcp:
        ignore.add("tcp")
    if args.ignore_udp:
        ignore.add("udp")
    if args.ignore_remote:
        ignore.add("remote")
    if args.ignore_kernel:
        ignore.add("proc-kernel")
    unknown = ignore - set(type_ids)
    if unknown:
        ap.error(
            "unknown class id(s): %s\nvalid ids: %s"
            % (", ".join(sorted(unknown)), ", ".join(type_ids))
        )

    is_root = os.geteuid() == 0
    procs = read_processes()
    socks = read_sockets()
    inode2pids = map_inode_pids(list(procs.keys()))
    model, unattributed = build_graph(procs, socks, inode2pids, is_root, ignore)

    json.dump(model, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    c = model["meta"]["counts"]
    print(
        "sockets_graph: %s — %d nodes, %d edges%s"
        % (
            model["meta"]["title"],
            c["nodes"],
            c["edges"],
            "" if is_root else " (unprivileged; sudo for full attribution)",
        ),
        file=sys.stderr,
    )
    if unattributed and not is_root:
        print(
            "  %d sockets not attributed to a process" % unattributed,
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
