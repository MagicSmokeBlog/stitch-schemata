import math
from pathlib import Path
from typing import Any, Tuple

import cv2 as cv
import numpy as np


class Image:
    """
    Class for images.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, data: np.ndarray):
        """
        Object constructor.

        :param data: The image.
        """
        self._data: np.ndarray = data

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def data(self) -> np.ndarray:
        return self._data

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def width(self) -> int:
        """
        Returns the width of this image.
        """
        _, width = self._data.shape[:2]

        return width

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def height(self) -> int:
        """
        Returns the width of this image.
        """
        height, _ = self._data.shape[:2]

        return height

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def read(path: Path):
        """
        Reads an image from the given path.

        :param path: The path.
        """
        data = cv.imread(str(path))
        assert data is not None, f"Unable to open image '{path}'."

        return Image(data)

    # ------------------------------------------------------------------------------------------------------------------
    def write(self, path: Path, params: Any = None) -> None:
        """
        Writes the image to the given path.

        :param path: The path.
        :param params:
        """
        if params is None:
            cv.imwrite(str(path), self._data)
        else:
            cv.imwrite(str(path), self._data, params)

    # ------------------------------------------------------------------------------------------------------------------
    def rotate(self, angle: float):
        """
        Returns a copy of this image rotated by the given angle.

        :param angle: The angle in degrees.
        """
        width, height = self.size()
        center = (width // 2, height // 2)

        rotation_matrix = cv.getRotationMatrix2D(center, angle, 1.0)
        data = cv.warpAffine(self._data, rotation_matrix, self._data.shape[1::-1], )
        data = self._crop_around_center(data, *self._largest_rotated_rect(width, height, math.radians(angle)))

        return Image(data)

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _crop_around_center(data: np.ndarray, width: float, height: float) -> np.ndarray:
        """
        Given a image, crops it to the given width and height, around it's center point.
        """
        image_size = (data.shape[1], data.shape[0])
        image_center = (int(image_size[0] * 0.5), int(image_size[1] * 0.5))

        if width > image_size[0]:
            width = image_size[0]

        if height > image_size[1]:
            height = image_size[1]

        x1 = int(image_center[0] - width * 0.5)
        x2 = int(image_center[0] + width * 0.5)
        y1 = int(image_center[1] - height * 0.5)
        y2 = int(image_center[1] + height * 0.5)

        return data[y1:y2, x1:x2]

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _largest_rotated_rect(width: int, height: int, angle: float):
        """
        Given a rectangle of size wxh that has been rotated by an angle (in radians), computes the width and height of
        the largest possible axis-aligned rectangle within the rotated rectangle.

        See https://stackoverflow.com/questions/16702966/rotate-image-and-crop-out-black-borders.
        """
        quadrant = int(math.floor(angle / (math.pi / 2))) & 3
        sign_alpha = angle if ((quadrant & 1) == 0) else math.pi - angle
        alpha = (sign_alpha % math.pi + math.pi) % math.pi

        bb_width = width * math.cos(alpha) + height * math.sin(alpha)
        bb_height = width * math.sin(alpha) + height * math.cos(alpha)

        if width < height:
            gamma = math.atan2(bb_width, bb_width)
        else:
            gamma = math.atan2(bb_width, bb_width)

        delta = math.pi - alpha - gamma

        if width < height:
            length = height
        else:
            length = width

        d = length * math.cos(alpha)
        a = d * math.sin(alpha) / math.sin(delta)

        y = a * math.cos(gamma)
        x = y * math.tan(gamma)

        return bb_width - 2 * x, bb_height - 2 * y

    # ------------------------------------------------------------------------------------------------------------------
    def grayscale(self):
        """
        Returns a grayscale copy of this image.
        """
        return Image(cv.cvtColor(self._data, cv.COLOR_BGR2GRAY))

    # ------------------------------------------------------------------------------------------------------------------
    def size(self) -> Tuple[int, int]:
        """
        Returns the size (width and height) of this image.
        """
        height, width = self._data.shape[:2]

        return width, height

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def merge_data(destination: np.ndarray,
                   source: np.ndarray,
                   offset_x: int,
                   offset_y: int,
                   overlap_x: int) -> np.ndarray:
        """
        Copies one image into another image.

        :param destination: The destination image.
        :param source: The source image to be copied.
        :param offset_x: The offset along the x-axis where the source image must be copied into the destination image.
        :param offset_y: The offset along the y-axis where the source image must be copied into the destination image.
        :param overlap_x: The offset along the x-axis from where the source image must be copied.
        """
        height1, width1 = destination.shape[:2]
        height2, width2 = source.shape[:2]

        x1_min = max(0, offset_x + overlap_x)
        x1_max = min(width1, width2 + offset_x)
        y1_min = max(0, offset_y)
        y1_max = min(height1, height2 + offset_y)

        y2_min = max(0, -offset_y)
        y2_max = y2_min + y1_max - y1_min
        x2_min = max(0, overlap_x)
        x2_max = min(width2, width2 + offset_x)

        destination[y1_min:y1_max, x1_min:x1_max] = source[y2_min:y2_max, x2_min:x2_max]

        return destination

# ----------------------------------------------------------------------------------------------------------------------
