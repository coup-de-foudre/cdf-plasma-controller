#!/usr/bin/env python3
"""Rewrite a .iannix score so its OSC messages target localhost.

The production score sends to `osc://192.168.1.255:5005/...` (the gallery
LAN broadcast address). On a development Mac that's nowhere — packets
either bounce off the default route or vanish. This script makes a copy of
the score with every `setmessage` URL rewritten to `127.0.0.1:5005` so the
local OSC sink (`extras/iannix/osc_sink.py`) can capture it.

Usage:
    python3 extras/iannix/rewrite_for_localhost.py \\
        extras/iannix/P-Tubes_w-SC_MM_G-2.iannix \\
        extras/iannix/P-Tubes_w-SC_MM_G-2.localhost.iannix
"""
import re
import sys


# Match `osc://<host>:<port>` inside the IanniX setmessage strings. We keep
# the original port (5005 in practice) but force the host to 127.0.0.1.
_OSC_RE = re.compile(r'osc://[^:/\s]+:(\d+)/')


def rewrite(text: str, host: str = "127.0.0.1") -> str:
    return _OSC_RE.sub(r'osc://' + host + r':\1/', text)


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__, file=sys.stderr)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    host = sys.argv[3] if len(sys.argv) == 4 else "127.0.0.1"
    with open(src, 'r') as fp:
        text = fp.read()
    out = rewrite(text, host)
    n = len(_OSC_RE.findall(text))
    with open(dst, 'w') as fp:
        fp.write(out)
    print("rewrote {} OSC URLs in {} -> {}".format(n, src, dst))
    return 0


if __name__ == '__main__':
    sys.exit(main())
