from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.Tile import Tile


class TileFinder:
    """
    Class for finding a tile in a scanned page.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 io: StitchSchemataIO,
                 config: Config,
                 image: Image,
                 vertical_band_x: int | None = None,
                 vertical_band_width: int | None = None):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param image: The grayscale image of the scanned page.
        :param vertical_band_x: The left x-coordinate of on an optional vertical band where to match the tile.
        :param vertical_band_width: The width of an optional vertical band where to match the tile.
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

        self._vertical_band_x: int | None = vertical_band_x
        """
        The left x-coordinate of on an optional vertical band where to match the tile.
        """

        self._vertical_band_width: int | None = vertical_band_width
        """
        The width of an optional vertical band where to match the tile.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def find_tile(self, tile: Tile) -> Tile:
        """
        Finds the best matching part in the scanned page with a tile.

        :param tile: The tile.
        """
        y_start = max(tile.y - self._config.vertical_offset_max, 0)
        y_stop = min(tile.y + tile.image.height + self._config.vertical_offset_max, self._image.height)
        x_start = self._vertical_band_x or 0
        width = self._vertical_band_width or self._image.width
        image_band = self._image.sub_image(x_start, y_start, width, y_stop - y_start)
        x, y, match = image_band.match_template(tile.image)
        x = x + x_start
        y = y + y_start
        self._io.log_verbose(f'Found tile at ({x}, {y}), match: {match}.')

        return Tile(x=x,
                    y=y,
                    match=match,
                    shapes=None,
                    image=self._image.sub_image(x, y, tile.image.width, tile.image.height),
                    area=((x_start, y_start), (x_start + width - 1, y_stop - 1)))

        # ----------------------------------------------------------------------------------------------------------------------
