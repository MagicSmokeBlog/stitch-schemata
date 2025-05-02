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
    def __init__(self,
                 io: StitchSchemataIO,
                 config: Config,
                 grayscale_page: Path,
                 tile_hint: Tuple[Tuple[int, int], Tuple[int, int]] | None = None):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param grayscale_page: Path to the grayscale image of the scanned page.
        :param tile_hint: The tile hint for the scanned page.
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

        self._tile_hint: Tuple[Tuple[int, int], Tuple[int, int]] = tile_hint
        """
        The tile hint for the scanned page.
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
        if self._tile_hint is None:
            return self._extract_tiles_auto()

        return self._extract_tiles_manual()

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tiles_manual(self) -> Tuple[Tile, Tile]:
        """
        Extracts the top and bottom tiles in a scanned page give a tile hint.
        """
        tile_top = self._extract_tile_manual_top()
        tile_bottom = self._extract_tile_manual_bottom()

        return tile_top, tile_bottom

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_manual_top(self) -> Tile:
        """
        Extracts the top and bottom tiles in a scanned page give a tile hint.
        """
        width, height = self._image.size()
        y_lt = int(self._tile_hint[0][1])
        x_lt = int(self._tile_hint[0][0])
        x_rb = x_lt + int(self._config.tile_width)
        y_rb = y_lt + int(self._config.tile_height)

        x_lt = max(0, x_lt)
        y_lt = max(0, y_lt)
        x_rb = min(width - 1, x_rb)
        y_rb = min(height - 1, y_rb)

        tile = self._image.data[y_lt:y_rb + 1, x_lt:x_rb + 1]
        contrast = tile.std()

        return Tile(x=x_lt,
                    y=y_lt,
                    contrast=contrast,
                    width=self._config.tile_width,
                    height=self._config.tile_height,
                    image=tile)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_manual_bottom(self) -> Tile:
        """
        Extracts the top and bottom tiles in a scanned page give a tile hint.
        """
        width, height = self._image.size()
        y_lt = int(self._tile_hint[1][1])
        x_lt = int(self._tile_hint[1][0])
        x_rb = x_lt + int(self._config.tile_width)
        y_rb = y_lt + int(self._config.tile_height)

        x_lt = max(0, x_lt)
        y_lt = max(0, y_lt)
        x_rb = min(width - 1, x_rb)
        y_rb = min(height - 1, y_rb)

        tile = self._image.data[y_lt:y_rb + 1, x_lt:x_rb + 1]
        contrast = tile.std()

        return Tile(x=x_lt,
                    y=y_lt,
                    contrast=contrast,
                    width=self._config.tile_width,
                    height=self._config.tile_height,
                    image=tile)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tiles_auto(self) -> Tuple[Tile, Tile]:
        """
        Extracts the top and bottom tiles in a scanned page automatically
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
        contrasts = []
        for j in range(start, stop):
            part = self._image.data[j:j + self._config.tile_height, i:i + self._config.tile_width]
            weight = 1.0 if j <= fraction else (j - fraction) / (fraction - stop)
            contrast = weight * part.std()
            if contrast > contrast_max:
                contrast_max = contrast
                j_max = j
            contrasts.append(contrast)

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
        # stop = height // 2
        for j in range(start, fraction, -1):
            part = self._image.data[j:j + self._config.tile_height, i:i + self._config.tile_width]
            # weight = 1.0 if j >= fraction else (fraction - j) / (stop - fraction)
            weight = 1.0
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
