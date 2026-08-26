"""Startet WerkMate direkt aus dem Projektordner, auch ohne Installation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from werkmate.gui import main  # noqa: E402


if __name__ == "__main__":
    main()

