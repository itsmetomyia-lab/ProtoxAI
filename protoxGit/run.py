# -*- coding: utf-8 -*-
"""PROTOX AI // v2.3.0 — Entry Point"""

import logging
import sys

# Configura logging base (DEBUG su file, WARNING su console)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

from protox.app import ProtoxIDE

if __name__ == "__main__":
    app = ProtoxIDE()
    app.run()
