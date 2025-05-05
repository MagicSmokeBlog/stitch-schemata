import math

import cv2
import numpy as np

from stitch_schemata.stitch.Image import Image


class OrientationDetector:
    """
    Class for detecting the orientation, i.e., the rotation, of an image.
    """

    def __init__(self, grayscale_image: Image):
        """
        Object constructor.

        :param grayscale_image: The grayscale image.
        """
        self._grayscale_image = grayscale_image

    # ------------------------------------------------------------------------------------------------------------------
    def detect_orientation(self) -> float | None:
        """
        Returns the orientation of the image in degrees. Return None when the orientation isn't detected.
        """
        thresh = cv2.inRange(self._grayscale_image.data, 0, 110)
        edges = cv2.Canny(thresh, 150.0, 150.0)
        hough_lines = cv2.HoughLinesP(edges,
                                      rho=1,
                                      theta=np.pi / 1800.0,
                                      threshold=100,
                                      minLineLength=100,
                                      maxLineGap=25)
        length_min = 0.1 * max(self._grayscale_image.size())
        angles = []
        for hough_line in hough_lines:
            x1, y1, x2, y2 = hough_line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            length = math.hypot(x2 - x1, y2 - y1)
            if length > length_min:
                if abs(angle) < 1.0:
                    angles.append(angle)
                if abs(angle - 90.0) < 1.0:
                    angles.append(angle - 90.0)

        if len(angles) == 0:
            return None

        return float(np.average(angles))

# ----------------------------------------------------------------------------------------------------------------------
