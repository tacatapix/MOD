"""Top-level launcher -- ``python EconomiaApp.py``."""

import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "src")
if src not in sys.path:
    sys.path.insert(0, src)

from gui import main  # noqa: E402

if __name__ == "__main__":
    main()
