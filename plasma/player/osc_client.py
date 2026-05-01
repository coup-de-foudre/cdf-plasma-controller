#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Thin wrapper around python-osc's UDP client.

The score player only needs three OSC messages — `/<root>/start`,
`/<root>/stop`, and `/<root>/fine/value <float>`. This module wraps the
client so the rest of the player code doesn't have to know about the OSC
address layout.
"""
import logging
import time

from pythonosc import udp_client


logger = logging.getLogger(__name__)


# Spacing between repeated /stop messages in the long-press kill. UDP loopback
# loss is essentially zero, but this is the "kill the show" path.
_KILL_STOP_COUNT = 3
_KILL_STOP_INTERVAL_S = 0.05


class PlayerOSCClient:
    def __init__(self, host: str, port: int, root: str):
        self._client = udp_client.SimpleUDPClient(host, port)
        # Strip leading/trailing slashes from `root`, mirroring OSCController.
        self._root = root.strip('/')
        self._host = host
        self._port = port
        logger.info("OSC client targeting %s:%s, root=%r",
                    host, port, self._root)

    def _path(self, suffix: str) -> str:
        return "/{}/{}".format(self._root, suffix.lstrip('/'))

    def start(self) -> None:
        path = self._path("start")
        logger.debug("send %s", path)
        self._client.send_message(path, [])

    def stop(self) -> None:
        path = self._path("stop")
        logger.debug("send %s", path)
        self._client.send_message(path, [])

    def fine_value(self, value: float) -> None:
        path = self._path("fine/value")
        # The receiving handler clips to [-1, 1]; we don't need to clip here.
        self._client.send_message(path, float(value))

    def kill(self) -> None:
        """Long-press kill: send /stop multiple times to be paranoid."""
        for i in range(_KILL_STOP_COUNT):
            self.stop()
            if i < _KILL_STOP_COUNT - 1:
                time.sleep(_KILL_STOP_INTERVAL_S)
