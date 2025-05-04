import math
from pathlib import Path
from typing import Tuple

import cv2 as cv

from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.StitchError import StitchError
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
            tile_top, tile_bottom = self._extract_tiles_auto()
        else:
            tile_top, tile_bottom = self._extract_tiles_manual()

        self._io.log_verbose(f'Top tile: ({tile_top.x},{tile_top.y}), contrast: {tile_top.contrast}.')
        self._io.log_verbose(f'Bottom tile: ({tile_bottom.x},{tile_bottom.y}), contrast: {tile_bottom.contrast}.')
        if self._io.is_very_verbose():
            target_path = self._grayscale_page.with_name(f'{self._grayscale_page.stem}-tile-top.png')
            cv.imwrite(str(target_path), tile_top.image)
            target_path = self._grayscale_page.with_name(f'{self._grayscale_page.stem}-tile-bottom.png')
            cv.imwrite(str(target_path), tile_bottom.image)

        return tile_top, tile_bottom

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
        width, height = self._image.size()

        min_x = self._config.margin
        max_x = min(int(self._config.overlap_min * width), width - self._config.margin - 1)
        bands_x = int(math.ceil((max_x - min_x + 1) / (0.5 * self._config.tile_width)))
        step_x = int(math.ceil((max_x - min_x + 1) / bands_x))

        min_y = self._config.margin
        max_y = height - self._config.margin - 1
        bands_y = int(math.ceil((max_y - min_y + 1) / (0.5 * self._config.tile_height)))
        step_y = int(math.ceil((max_y - min_y + 1) / bands_y))

        tiles = []
        for x in range(min_x, max_x + 1, step_x):
            for y in range(min_y, max_y + 1, step_y):
                data = self._image.data[y:y + self._config.tile_width + 1, x:x + self._config.tile_height + 1]
                contrast = data.std()
                if contrast >= self._config.tile_contrast_min:
                    tile = Tile(x=x, y=y, contrast=contrast, width=width, height=height, image=data)
                    tiles.append(tile)

        distance_max = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)
        contrast_max = max([tile.contrast for tile in tiles])

        n = len(tiles)
        value_max = 0.0
        tile1_max: Tile | None = None
        tile2_max: Tile | None = None
        for i in range(n):
            tile1 = tiles[i]
            for j in range(i + 1, n):
                tile2 = tiles[j]
                distance = math.sqrt((tile2.x - tile1.x) ** 2 + (tile2.y - tile1.y) ** 2)
                if distance > math.sqrt(self._config.tile_width ** 2 + self._config.tile_height ** 2):
                    value = (tile1.contrast + tile2.contrast) / contrast_max + distance / distance_max
                    if value > value_max:
                        value_max = value
                        tile1_max = tile1
                        tile2_max = tile2

        if tile1_max is None or tile2_max is None:
            raise StitchError(f'Unable to find tiles in image {self._grayscale_page} with sufficient contrast.')

        if tile1_max.y < tile2_max.y:
            return tile1_max, tile2_max

        return tile2_max, tile1_max

# ----------------------------------------------------------------------------------------------------------------------
