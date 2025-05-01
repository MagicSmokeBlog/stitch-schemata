from pathlib import Path
from typing import Tuple

import cv2 as cv

from stitch_schemata.helper.Config import Config
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.Tile import Tile


class TileExtractor:
    """
    Class for extracting top and bottom tiles from a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: StitchSchemataIO, config: Config, grayscale_page: Path):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param grayscale_page: Path to the grayscale image of the scanned page.
        """
        self._io: StitchSchemataIO = io
        """
        The Output decorator.
        """

        self._config: Config = config
        """
        The configuration.
        """

        self._grayscale_page: Path = grayscale_page
        """
        Path to the grayscale image of the scanned page.
        """

        self._image: Image = Image.read(self._grayscale_page)
        """
        The image of the scanned page.
        """

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def width(self) -> int:
        """
        The width of the scanned page after rotation.
        """
        return self._image.width

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def height(self) -> int:
        """
        The height of the scanned page after rotation.
        """
        return self._image.height

    # ------------------------------------------------------------------------------------------------------------------
    def extract_tiles(self) -> Tuple[Tile, Tile]:
        """
        Extracts the top and bottom tiles in a scanned page.
        """
        tile_top = self._extract_tile_top()
        tile_bottom = self._extract_tile_bottom()

        return tile_top, tile_bottom

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_top(self) -> Tile:
        """
        Extracts the top tile.
        """
        width, height = self._image.size()

        i = self._config.margin
        contrast_max = 0.0
        j_max = 0
        start = self._config.margin
        fraction = int(height * self._config.tile_fraction)
        stop = height // 2
        for j in range(start, stop):
            part = self._image.data[j:j + self._config.tile_height, i:i + self._config.tile_width]
            weight = 1.0 if j <= fraction else (j - fraction) / (fraction - stop)
            contrast = weight * part.std()
            if contrast > contrast_max:
                contrast_max = contrast
                j_max = j

        tile = self._image.data[j_max:j_max + self._config.tile_height, i:i + self._config.tile_width]

        message = f"Top tile: ({i}, {j_max})x({i + self._config.tile_width - 1}, {j_max + self._config.tile_height - 1})."
        self._io.log_verbose(message)
        self._io.log_verbose(f'Contrast: {contrast_max}')
        if self._io.is_very_verbose():
            target_path = self._grayscale_page.with_name(f'{self._grayscale_page.stem}-tile-top.png')
            cv.imwrite(str(target_path), tile)

        return Tile(x=i,
                    y=j_max,
                    contrast=contrast_max,
                    width=self._config.tile_width,
                    height=self._config.tile_height,
                    image=tile)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_bottom(self) -> Tile:
        """
        Extracts the bottom tile.
        """
        width, height = self._image.size()

        i = self._config.margin
        contrast_max = 0.0
        j_max = 0
        start = height - 1 - self._config.margin - self._config.tile_height
        fraction = height - int(height * self._config.tile_fraction)
        stop = height // 2
        for j in range(start, stop, -1):
            part = self._image.data[j:j + self._config.tile_height, i:i + self._config.tile_width]
            weight = 1.0 if j >= fraction else (fraction - j) / (stop - fraction)
            contrast = weight * part.std()
            if contrast > contrast_max:
                contrast_max = contrast
                j_max = j

        tile = self._image.data[j_max:j_max + self._config.tile_height, i:i + self._config.tile_width]

        message = f"Bottom tile: ({i}, {j_max})x({i + self._config.tile_width - 1}, {j_max + self._config.tile_height - 1})."
        self._io.log_verbose(message)
        self._io.log_verbose(f'Contrast: {contrast_max}')
        if self._io.is_very_verbose():
            target_path = self._grayscale_page.with_name(f'{self._grayscale_page.stem}-tile-bottom.png')
            cv.imwrite(str(target_path), tile)

        return Tile(x=i,
                    y=j_max,
                    contrast=contrast_max,
                    width=self._config.tile_width,
                    height=self._config.tile_height,
                    image=tile)

# ----------------------------------------------------------------------------------------------------------------------
