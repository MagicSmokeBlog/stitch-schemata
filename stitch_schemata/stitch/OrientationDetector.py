import math
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch import debug_seq_value
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image


class OrientationDetector:
    """
    Class for detecting the orientation, i.e., the rotation, of an image.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 io: StitchSchemataIO,
                 config: Config,
                 path: Path,
                 grayscale_image: Image):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param path: The path to the original scanned page.
        :param grayscale_image: The grayscale image.
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

        self._grayscale_image = grayscale_image
        """
        The grayscale image.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def detect_orientation(self) -> float | None:
        """
        Returns the orientation of the image in degrees. Returns None when the orientation isn't detected.
        """
        thresh = cv2.inRange(self._grayscale_image.data, 0, 110)
        edges = cv2.Canny(thresh, 150.0, 150.0)
        hough_lines = cv2.HoughLinesP(edges,
                                      rho=1,
                                      theta=np.pi / 1800.0,
                                      threshold=100,
                                      minLineLength=100,
                                      maxLineGap=25)
        length_min = 0.1 * max(self._grayscale_image.size)
        angles = []
        lines = []
        if hough_lines is not None:
            for hough_line in hough_lines:
                x1, y1, x2, y2 = hough_line[0]
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                length = math.hypot(x2 - x1, y2 - y1)
                if length > length_min:
                    if abs(angle) < self._config.rotation_max:
                        angles.append(angle)
                        lines.append((x1, y1, x2, y2))
                    if abs(angle - 90.0) < self._config.rotation_max:
                        angles.append(angle - 90.0)
                        lines.append((x1, y1, x2, y2))
                    if abs(angle + 90.0) < self._config.rotation_max:
                        angles.append(angle + 90.0)
                        lines.append((x1, y1, x2, y2))

        self._debug_save_page_hough_lines(lines)

        if len(angles) == 0:
            return None

        angle = float(np.average(angles))

        self._io.log_verbose(f'Rotation {angle}.')

        return angle

    # ------------------------------------------------------------------------------------------------------------------
    def _debug_save_page_hough_lines(self, lines: List[Tuple[int, int, int, int]]) -> None:
        """
        Saves scanned page with found lines for debugging purposes.

        :param lines: The found lines.
        """
        color = (0, 0, 255)
        width = 2

        path = self._config.tmp_path / f'{debug_seq_value():02d}-page-{0}.png'
        image = cv2.cvtColor(self._grayscale_image.data, cv2.COLOR_GRAY2RGB)
        for line in lines:
            x1, y1, x2, y2 = line
            cv2.rectangle(image, (x1, y1), (x2, y2), color, width)
        cv2.imwrite(str(path), image)

# ----------------------------------------------------------------------------------------------------------------------
