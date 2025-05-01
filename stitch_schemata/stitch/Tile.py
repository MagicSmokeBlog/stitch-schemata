from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Tile:
    """
    A tile.
    """

    # ------------------------------------------------------------------------------------------------------------------
    x: int = 0
    """
    Top x-coordinate of the left top of the tile.
    """

    y: int = 0
    """
    Top y-coordinate of the left top of the tile.
    """

    match: float | None = None
    """
    The 
    """

    contrast: float | None = None
    """
    The contrast of the tile.
    """

    width: int = 0
    """
    Width of the tile.
    """

    height: int = 0
    """
    Height of the tile.
    """

    image: np.ndarray | None = None
    """
    The tile image.
    """

# ----------------------------------------------------------------------------------------------------------------------
