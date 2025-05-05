from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Tile:
    """
    A tile.
    """

    # ------------------------------------------------------------------------------------------------------------------
    x: int
    """
    Top x-coordinate of the left top of the tile.
    """

    y: int
    """
    Top y-coordinate of the left top of the tile.
    """

    match: float | None
    """
    The 
    """

    contrast: float | None
    """
    The contrast of the tile.
    """

    width: int
    """
    Width of the tile.
    """

    height: int
    """
    Height of the tile.
    """

    image: np.ndarray
    """
    The tile image.
    """

# ----------------------------------------------------------------------------------------------------------------------
