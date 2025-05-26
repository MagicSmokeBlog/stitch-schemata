from dataclasses import dataclass
from typing import Tuple

from stitch_schemata.stitch.Image import Image


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

    shapes: int | None
    """
    The number of shapes in this tile.
    """

    image: Image
    """
    The tile image.
    """

    area: Tuple[Tuple[int, int], Tuple[int, int]] | None = None
    """
    The search area of the tile.
    """

# ----------------------------------------------------------------------------------------------------------------------
