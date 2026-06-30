# Format Python source with black
format:
    black render-graph-html.py

# Cats the viewer (all under `class Viewer`) + the generator + the glue, after
# linting the generator against the conventions (see README "Generator conventions").
#   just bundle sockets_graph.py   ->  dist/sockets_graph.py  (generate + render in one)
#   just bundle lspgraph.py calls.py
# Fuse render-graph-html.py + a generator into one standalone runnable script (dist/).
bundle gen out="":
    #!/usr/bin/env bash
    set -euo pipefail
    gen="{{gen}}"
    [ -f "$gen" ] || { echo "bundle: generator not found: $gen" >&2; exit 1; }
    out="{{out}}"
    [ -n "$out" ] || out="dist/$(basename "$gen")"
    if [ "$out" = "$gen" ] || [ "$(basename "$out")" = "render-graph-html.py" ]; then
      echo "bundle: refusing to overwrite a source file ($out)" >&2; exit 1
    fi
    # --- lint generator conventions (see README) ---
    grep -qE '^def main\b' "$gen" || { echo "bundle: $gen has no top-level main() (convention C1)" >&2; exit 1; }
    if grep -qE '^class Viewer\b|^Viewer *=' "$gen"; then
      echo "bundle: $gen defines top-level \`Viewer\`, reserved for the renderer namespace (C3). See README 'Generator conventions'." >&2; exit 1
    fi
    if grep -qE '"-o"|"--out"' "$gen"; then
      echo "bundle: $gen defines -o/--out, reserved by the bundle for HTML output (C2)." >&2; exit 1
    fi
    mkdir -p "$(dirname "$out")"
    {
      sed '/^if __name__ == "__main__":/,$d' render-graph-html.py
      sed '/^if __name__ == "__main__":/,$d' "$gen"
      cat bundle_main.py
    } > "$out"
    black -q "$out"
    chmod +x "$out"
    echo "wrote $out ($(wc -l < "$out") lines) — run: ./$out [generator args] > out.html"

# Bundle every generator (every *.py except the viewer and the glue) into dist/.
bundle-all:
    #!/usr/bin/env bash
    set -euo pipefail
    n=0
    for gen in *.py; do
      case "$gen" in render-graph-html.py | bundle_main.py) continue ;; esac
      just bundle "$gen"
      n=$((n + 1))
    done
    echo "bundle-all: $n generator(s) -> dist/"
