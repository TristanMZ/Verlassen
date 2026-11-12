"""
Verlassen
=========
A 2D story-driven stealth game about escape, truth, and poverty.
"""

from __future__ import annotations

import sys
from core.game import Game


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

