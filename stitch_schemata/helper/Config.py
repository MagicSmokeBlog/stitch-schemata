from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class Config:
    """
    The configuration of StichSchemata.
    """
    margin: int = 20
    """
    The margin applied when searching for tiles. 
    """

    overlap_min: float = 0.1
    """
    The minimum overlap fraction of scanned pages.
    """

    vertical_offset_max: int = 50
    """
    The maximum vertical offset in pixels of the scanned pages.
    """

    tile_width: int = 200
    """
    The width of a tile.
    """

    tile_height: int = 200
    """
    The height of a tile.
    """

    tile_contrast_min: float = 10.0
    """
    The minimum required contrast for find the top and bottom tiles.
    """

    tile_match_min: float = 0.8
    """
    The minimum required match for finding a tile.
    """

    tile_iterations_max: int = 5
    """
    The maximum number of iterations allowed for finding a tile.
    """

    tmp_path: Path = Path('.')
    """
    The path to the temp folder. 
    """

    output_path: Path = Path('stitched.png')
    """
    The path to the stitched output file. 
    """

    quality: int = 90
    """
    The quality of the stitched image when saved as jpeg or pdf. 
    """

    tile_hints: Dict[str,Tuple[Tuple[int,int],Tuple[int,int]]] = None
    """
    Manual given hints for finding tiles. A map from basename of scanned images to the centers of the top and bottom 
    tiles. 
    """