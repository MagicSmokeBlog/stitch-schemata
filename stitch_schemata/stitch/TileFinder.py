import cv2 as cv

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.Tile import Tile


class TileFinder:
    """
    Class for finding a tile in a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: StitchSchemataIO, config: Config, image: Image):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param image: The grayscale image of the scanned page.
        """
        self._io: StitchSchemataIO = io
        """
        The Output decorator.
        """

        self._config: Config = config
        """
        The configuration.
        """

        self._image: Image = image
        """
        The grayscale image of the scanned page.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def find_tile(self, tile: Tile) -> Tile:
        """
        Finds the best matching part in the scanned page with a tile.

        :param tile: The tile.
        """
        start = max(tile.y - self._config.vertical_offset_max, 0)
        stop = min(tile.y + tile.image.height + self._config.vertical_offset_max, self._image.height)
        image_band = self._image.data[start:stop]
        res = cv.matchTemplate(image_band, tile.image.data, cv.TM_CCOEFF_NORMED)
        _, match, _, location = cv.minMaxLoc(res)
        self._io.log_verbose(f'Found tile at {location}, match: {match}.')

        return Tile(x=location[0],
                    y=location[1] + start,
                    match=match,
                    contrast=None,
                    image=Image(self._image.data[location[1]:location[1] + tile.image.height,
                                location[0]:location[0] + tile.image.width]))

# ----------------------------------------------------------------------------------------------------------------------
