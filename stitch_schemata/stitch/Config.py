from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class Config:
    """
    The configuration of StichSchemata.
    """
    margin: int
    """
    The margin applied when searching for tiles. 
    """

    overlap_min: float
    """
    The minimum overlap fraction of scanned pages.
    """

    vertical_offset_max: int
    """
    The maximum vertical offset in pixels of the scanned pages.
    """

    tile_width: int
    """
    The width of a tile.
    """

    tile_height: int
    """
    The height of a tile.
    """

    tile_contrast_min: float
    """
    The minimum required contrast for find the top and bottom tiles.
    """

    tile_match_min: float
    """
    The minimum required match for finding a tile.
    """

    tile_iterations_max: int
    """
    The maximum number of iterations allowed for finding a tile.
    """

    tmp_path: Path
    """
    The path to the temp folder. 
    """

    output_path: Path
    """
    The path to the stitched output file. 
    """

    crop: bool
    """
    Whether to crop the image. Only effects to top and bottom part of the stitched image.
    """

    quality: int
    """
    The quality of the stitched image when saved as jpeg or pdf. 
    """

    tile_hints: Dict[str,Tuple[Tuple[int,int],Tuple[int,int]]]
    """
    Manual given hints for finding tiles. A map from basename of scanned images to the centers of the top and bottom 
    tiles. 
    """