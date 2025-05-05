from dataclasses import dataclass

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

    contrast: float | None
    """
    The contrast of the tile.
    """

    image: Image
    """
    The tile image.
    """

# ----------------------------------------------------------------------------------------------------------------------
