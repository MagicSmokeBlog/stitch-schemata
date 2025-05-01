from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScanMetadata:
    """
    The metadata and operations of a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    path: Path = Path()
    """
    The path to the scanned page.
    """

    rotate: float = 0.0
    """
    The angle of rotation in degrees.
    """

    translate_x: int = 0
    """
    The translation along the x-axis.
    """

    translate_y: int = 0
    """
    The translation along the y-axis.
    """

    width: int = 0
    """
    The image width of the scanned page after rotation.
    """

    height: int = 0
    """
    The image height of the scanned page after rotation.
    """

# ----------------------------------------------------------------------------------------------------------------------
