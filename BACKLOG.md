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

- [ ] **jq-style query box** over the embedded JSON objects — a power-user
      complement to the substring/regex search (the natural next step now that
      the data is already one clean JSON model in the page).
- [ ] **Trace chain** upgrades:
  - [ ] hop-limit / depth knob
  - [ ] seed the trace from a **remote endpoint inward**
  - [ ] **export the traced chain** (JSON/CSV)
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

## Quality / engineering

- [ ] **Tests** for the `/proc` parsers (fixture-based) + minimal CI.
- [ ] **Performance**: replace the O(N²) repulsion with a Barnes-Hut/quadtree
      approximation for very large hosts; cap/warn on huge graphs.
