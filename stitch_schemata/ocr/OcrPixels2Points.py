from typing import Tuple


class OcrPixels2Points:
    """
    Helper class for converting coordinates given by Tesseract to coordinates on a PDF.
    """

    PPI: float = 72.0
    """
    The number of points per inch.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, width: int, height: int, dpi: int):
        """
        Object constructor.

        :param width: The width of the image in pixels.
        :param height: The width of the image in pixels.
        :param dpi: The dots per inch of the image.
        """
        self.width: int = width
        """
        The width of the image in pixels.
        """

        self.height: int = height
        """
        The height of the image in pixels.
        """

        self._dpi: int = dpi
        """
        The dots per inch of the image.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def map_pixels(self, pixels: int) -> float:
        """
        Maps pixels to points.

        :param pixels: The number of pixels.
        """
        return self.PPI * pixels / self._dpi

    # ------------------------------------------------------------------------------------------------------------------
    def map_coordinates(self, left: int, top: int, height: int) -> Tuple[float, float]:
        """
        Maps a coordinate in pixels to a coordinate in points.

        :param left: The x-coordinate.
        :param top: The y-coordinate.
        :param height: The height of the box in pixels.
        """
        return (self.PPI * left / self._dpi,
                self.PPI * (self.height - top - height) / self._dpi)

    # ------------------------------------------------------------------------------------------------------------------
    def map_box(self, left: int, top: int, length: int, height: int) -> Tuple[float, float, float, float]:
        """
        Maps a box in pixels to a box points.

        :param left: The x-coordinate.
        :param top: The y-coordinate.
        :param length: The length of the box in pixels.
        :param height: The height of the box in pixels.
        """
        return (self.PPI * left / self._dpi,
                self.PPI * (self.height - top - height) / self._dpi,
                self.PPI * length / self._dpi,
                self.PPI * height / self._dpi)

# ----------------------------------------------------------------------------------------------------------------------
