# ---------------------------------------------------------------------------
# bundled entry point  (appended by `just bundle`)
# ---------------------------------------------------------------------------
# This is the glue tail of a generated single-file bundle:
#   render-graph-html.py (viewer)  +  <generator>.py  +  this.
# The two sources are catted in with their `if __name__` trailers stripped, so
# everything is in scope here. The viewer lives entirely under `class Viewer`
# (its only top-level name), and the generator is catted last so the sole
# top-level `main` is the generator's. We run that `main()`, capture the model
# JSON it writes to stdout, and render it to one self-contained HTML file — i.e.
# the generator + the viewer fused into one runnable script.
#
# This works for ANY generator that follows the conventions (see README,
# "Generator conventions"): a top-level `main()` that dumps the model as JSON to
# stdout and returns on success; no `-o`/`--out` flag (reserved here for HTML
# output); and no top-level name `Viewer`.
import io
import contextlib


def _bundle_main():
    argv = sys.argv[1:]
    # Pull out -o/--out ourselves (the generator's parser doesn't know it); the
    # rest (its own flags, -h/--help) is left to the generator's main()
    # unchanged, so the bundle never duplicates or drifts from those flags.
    out_arg = None
    for flag in ("-o", "--out"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                out_arg = argv[i + 1]
                del argv[i : i + 2]
            break

    # Run the generator's main(), capturing the model JSON it writes to stdout.
    # Its one-line summary still goes to stderr (informative; stdout stays the
    # HTML stream when piped).
    buf = io.StringIO()
    saved = sys.argv
    sys.argv = [sys.argv[0]] + argv
    exit_code = None
    try:
        with contextlib.redirect_stdout(buf):
            try:
                main()
            except SystemExit as e:
                # --help prints to stdout then exits; argparse/runtime errors
                # raise SystemExit (message to stderr, which isn't redirected).
                # Either way, pass the captured stdout through and propagate the
                # code instead of trying to render it as a model.
                exit_code = 0 if e.code is None else e.code
    finally:
        sys.argv = saved

    if exit_code is not None:
        sys.stdout.write(buf.getvalue())
        sys.exit(exit_code)

    model = json.loads(buf.getvalue())
    html = Viewer.emit_html(model)
    if out_arg is None:
        sys.stdout.write(html)
    else:
        base, to_stdout = Viewer.resolve_out(out_arg)
        path = Viewer.emit_output(html, base, ".html", to_stdout)
        if path:
            print("wrote: %s" % os.path.abspath(path), file=sys.stderr)


if __name__ == "__main__":
    _bundle_main()
