from pathlib import Path

import cv2 as cv

from stitch_schemata.helper.Config import Config
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.Tile import Tile


class TileFinder:
    """
    Class for finding a tile in a scanned page.
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

    # ------------------------------------------------------------------------------------------------------------------
    def find_tile(self, tile: Tile) -> Tile:
        """

        """
        image = Image.read(self._grayscale_page)

        res = cv.matchTemplate(image.data, tile.image, cv.TM_CCOEFF_NORMED)

        _, value, _, location = cv.minMaxLoc(res)
        self._io.log_verbose(f'Found tile at {location} {value}.')

        return Tile(x=location[0],
                    y=location[1],
                    match=value,
                    width=tile.width,
                    height=tile.height,
                    image=image.data[location[1]:location[1] + self._config.tile_height,
                          location[0]:location[0] + self._config.tile_width])

    # ------------------------------------------------------------------------------------------------------------------
