#!/usr/bin/env python3
"""OSC sink that captures IanniX's `/<root>/fine/value` stream into per-tube
CSVs suitable for `scores/`.

Run alongside IanniX (after rewriting the score with rewrite_for_localhost.py
so that messages land on 127.0.0.1):

    python3 extras/iannix/osc_sink.py --out scores/

Then in IanniX: File → Open → the *.localhost.iannix copy, hit play, let it
run for one full loop. Press Ctrl-C in this script when done; it cleanly
closes the per-root CSV files. Rows are also flushed to disk as they
arrive, so an unclean exit doesn't lose data.

Optional: `--duration N` auto-stops after N seconds.
"""
import argparse
import os
import re
import signal
import sys
import threading
import time
from typing import Dict, TextIO

# Use the vendored python-osc.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "vendor", "python-osc"))

from pythonosc import dispatcher, osc_server


_FINE_PATH_RE = re.compile(r'^/([^/]+)/fine/value$')


class StreamingRecorder:
    """Writes rows to per-root CSV files as messages arrive.

    Each root's first message anchors that root's t=0. The file is opened
    on first sight and flushed after every write so the data survives an
    abrupt termination.
    """

    def __init__(self, out_dir: str):
        self._out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self._files: Dict[str, TextIO] = {}
        self._t0: Dict[str, float] = {}
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def on_message(self, address: str, *args) -> None:
        m = _FINE_PATH_RE.match(address)
        if not m:
            return
        if not args:
            return
        root = m.group(1)
        try:
            value = float(args[0])
        except (TypeError, ValueError):
            return
        now = time.monotonic()
        with self._lock:
            if root not in self._files:
                path = os.path.join(self._out_dir, "{}.csv".format(root))
                fp = open(path, 'w')
                fp.write("# scores/{}.csv\n".format(root))
                fp.write("# Captured from IanniX OSC stream\n")
                fp.write("# t_seconds, fine_value      "
                         "(fine_value in [-1, 1])\n")
                self._files[root] = fp
                self._t0[root] = now
                self._counts[root] = 0
                print("[capture] first message for {} -> {}".format(
                    root, path), flush=True)
            t = now - self._t0[root]
            fp = self._files[root]
            fp.write("{:.4f}, {:.6f}\n".format(t, value))
            fp.flush()
            self._counts[root] += 1

    def close(self) -> None:
        with self._lock:
            for root in sorted(self._files):
                self._files[root].close()
                print("[capture] {}: {} samples".format(
                    root, self._counts[root]))
            self._files.clear()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--host', default='127.0.0.1',
        help='Bind host (default: %(default)s)')
    parser.add_argument(
        '--port', type=int, default=5005,
        help='Bind port (default: %(default)s)')
    parser.add_argument(
        '--out', default=os.path.join(_REPO_ROOT, 'scores'),
        help='Output directory for CSVs (default: %(default)s)')
    parser.add_argument(
        '--duration', type=float, default=None,
        help='Auto-stop after this many seconds (default: run until Ctrl-C)')
    args = parser.parse_args()

    rec = StreamingRecorder(args.out)

    disp = dispatcher.Dispatcher()
    disp.set_default_handler(rec.on_message)
    server = osc_server.ThreadingOSCUDPServer((args.host, args.port), disp)

    # Run the server on a daemon thread so we can safely call
    # server.shutdown() from the main thread (where the signal handler
    # sets the stop event).
    server_thread = threading.Thread(
        target=server.serve_forever, name="osc-server", daemon=True)

    stop_event = threading.Event()

    def _on_signal(_signum, _frame):
        # Just flip the flag — never call server.shutdown() from a signal
        # handler running on the server thread (it deadlocks waiting for
        # itself to exit).
        stop_event.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    print("[capture] listening on {}:{} -- Ctrl-C to stop"
          .format(args.host, args.port), flush=True)
    server_thread.start()

    try:
        stop_event.wait(timeout=args.duration)
    finally:
        print("\n[capture] shutting down...", flush=True)
        server.shutdown()
        server_thread.join(timeout=5.0)
        rec.close()
        if server_thread.is_alive():
            print("[capture] server thread did not exit cleanly",
                  file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
