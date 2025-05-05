from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScanMetadata:
    """
    The metadata and operations of a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    path: Path
    """
    The path to the scanned page.
    """

    rotate: float
    """
    The angle of rotation in degrees.
    """

    translate_x: int
    """
    The translation along the x-axis.
    """

    translate_y: int
    """
    The translation along the y-axis.
    """

    width: int
    """
    The image width of the scanned page after rotation.
    """

    height: int
    """
    The image height of the scanned page after rotation.
    """

# ----------------------------------------------------------------------------------------------------------------------
