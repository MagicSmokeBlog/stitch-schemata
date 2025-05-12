import math
from pathlib import Path
from typing import Tuple

import numpy as np

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.StitchError import StitchError
from stitch_schemata.stitch.Tile import Tile


class TileExtractor:
    """
    Class for extracting top and bottom tiles from a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 io: StitchSchemataIO,
                 config: Config,
                 path: Path,
                 grayscale_image: Image,
                 tile_hint: Tuple[Tuple[int, int], Tuple[int, int]] | None = None):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param path: The path to the original scanned page.
        :param grayscale_image: The grayscale image of the scanned page.
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

        self._path: Path = path
        """
        The path to the original scanned page.
        """

        self._grayscale_image: Image = grayscale_image
        """
        The grayscale image of the scanned page.
        """

        self._tile_hint: Tuple[Tuple[int, int], Tuple[int, int]] = tile_hint
        """
        The tile hint for the scanned page.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def extract_tiles(self) -> Tuple[Tile, Tile]:
        """
        Extracts the top and bottom tiles in a scanned page.
        """
        if self._tile_hint is None:
            tile_top, tile_bottom = self._extract_tiles_auto()
        else:
            tile_top, tile_bottom = self._extract_tiles_manual()

        self._io.log_verbose(f'Top tile: ({tile_top.x},{tile_top.y}), # shapes: {tile_top.shapes}.')
        self._io.log_verbose(f'Bottom tile: ({tile_bottom.x},{tile_bottom.y}), # shapes: {tile_bottom.shapes}.')

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
        kernel_size = (math.ceil(self._config.tile_kernel_fraction * self._config.tile_width) // 2 * 2 + 1,
                       math.ceil(self._config.tile_kernel_fraction * self._config.tile_height) // 2 * 2 + 1)

        width, height = self._grayscale_image.size
        y_lt = int(self._tile_hint[0][1])
        x_lt = int(self._tile_hint[0][0])
        x_rb = x_lt + int(self._config.tile_width)
        y_rb = y_lt + int(self._config.tile_height)

        x_lt = max(0, x_lt)
        y_lt = max(0, y_lt)
        x_rb = min(width - 1, x_rb)
        y_rb = min(height - 1, y_rb)

        tile = Image(self._grayscale_image.data[y_lt:y_rb + 1, x_lt:x_rb + 1])

        return Tile(x=x_lt, y=y_lt, match=None, shapes=tile.number_of_shapes(kernel_size), image=tile)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_manual_bottom(self) -> Tile:
        """
        Extracts the top and bottom tiles in a scanned page give a tile hint.
        """
        kernel_size = (math.ceil(self._config.tile_kernel_fraction * self._config.tile_width) // 2 * 2 + 1,
                       math.ceil(self._config.tile_kernel_fraction * self._config.tile_height) // 2 * 2 + 1)

        width, height = self._grayscale_image.size
        y_lt = int(self._tile_hint[1][1])
        x_lt = int(self._tile_hint[1][0])
        x_rb = x_lt + int(self._config.tile_width)
        y_rb = y_lt + int(self._config.tile_height)

        x_lt = max(0, x_lt)
        y_lt = max(0, y_lt)
        x_rb = min(width - 1, x_rb)
        y_rb = min(height - 1, y_rb)

        tile = Image(self._grayscale_image.data[y_lt:y_rb + 1, x_lt:x_rb + 1])

        return Tile(x=x_lt, y=y_lt, match=None, shapes=tile.number_of_shapes(kernel_size), image=tile)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tiles_auto(self) -> Tuple[Tile, Tile]:
        """
        Extracts the top and bottom tiles from a scanned page automatically
        """
        width, height = self._grayscale_image.size

        start_x = self._config.margin
        stop_x = min(int(self._config.overlap_min * width - self._config.tile_width),
                     width - self._config.tile_width - self._config.margin)
        iter_x = int(max(1, math.ceil((stop_x - start_x) / (0.5 * self._config.tile_width)) + 1))
        step_x = 0.0 if iter_x == 1 else (stop_x - start_x) / (iter_x - 1)

        start_y = self._config.margin
        stop_y = height - self._config.margin - self._config.tile_height
        iter_y = int(max(1, math.ceil((stop_y - start_y) / (0.5 * self._config.tile_height)) + 1))
        step_y = 0.0 if iter_y == 1 else (stop_y - start_y) / (iter_y - 1)

        kernel_size = (math.ceil(self._config.tile_kernel_fraction * self._config.tile_width) // 2 * 2 + 1,
                       math.ceil(self._config.tile_kernel_fraction * self._config.tile_height) // 2 * 2 + 1)

        tiles = []
        for i in range(iter_x):
            x = int(start_x + i * step_x)
            for j in range(iter_y):
                y = int(start_y + j * step_y)
                image = Image(self._grayscale_image.data[y:y + self._config.tile_height,
                              x:x + self._config.tile_width])
                number_of_shapes = image.number_of_shapes(kernel_size)
                if number_of_shapes >= self._config.tile_shapes_min:
                    tile = Tile(x=x, y=y, match=None, shapes=number_of_shapes, image=image)
                    tiles.append(tile)

        tile1_max: Tile | None = None
        tile2_max: Tile | None = None
        n = len(tiles)
        if n > 0:
            distance_max = math.sqrt((stop_x - start_x) ** 2 + (stop_y - start_y) ** 2)
            shapes_avg = float(np.average([tile.shapes for tile in tiles]))

            value_max = 0.0
            for i in range(n):
                tile1 = tiles[i]
                for j in range(i + 1, n):
                    tile2 = tiles[j]
                    distance = math.sqrt((tile2.x - tile1.x) ** 2 + (tile2.y - tile1.y) ** 2)
                    if distance > math.sqrt(self._config.tile_width ** 2 + self._config.tile_height ** 2):
                        value = (tile1.shapes + tile2.shapes) / shapes_avg + distance / distance_max
                        if value > value_max:
                            value_max = value
                            tile1_max = tile1
                            tile2_max = tile2

        if tile1_max is None or tile2_max is None:
            raise StitchError(f'Unable to find tiles in image {self._path} with sufficient shapes.')

        if tile1_max.y < tile2_max.y:
            return tile1_max, tile2_max

        return tile2_max, tile1_max

# ----------------------------------------------------------------------------------------------------------------------
