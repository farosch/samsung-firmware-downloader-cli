#!/usr/bin/env python3
"""Search Samsung support branches or keywords and download published firmware."""

import sys

from samsung_firmware.catalog import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
