import unittest

from stitch_schemata.stitch.Image import Image


class ImageTest(unittest.TestCase):
    # ------------------------------------------------------------------------------------------------------------------
    def test_grayscale_red(self) -> None:
        """
        Test conversion from BGR to grayscale with red channel.
        """
        red_image = Image.empty_color_image(5, 10, (0, 0, 255))
        gray_image = red_image.color_bgr2gray()
        bgr_image = gray_image.color_gray2bgr()

        width, height = gray_image.size
        expected = int(0.2989 * 255 + 0.5)
        for i in range(width):
            for j in range(height):
                self.assertEqual(gray_image.data[j, i], expected)
                self.assertEqual(bgr_image.data[j, i][0], expected)
                self.assertEqual(bgr_image.data[j, i][1], expected)
                self.assertEqual(bgr_image.data[j, i][2], expected)

    # ------------------------------------------------------------------------------------------------------------------
    def test_grayscale_green(self) -> None:
        """
        Test conversion from BGR to grayscale with green channel.
        """
        red_image = Image.empty_color_image(5, 10, (0, 255, 0))
        gray_image = red_image.color_bgr2gray()
        bgr_image = gray_image.color_gray2bgr()

        width, height = gray_image.size
        expected = int(0.5870 * 255 + 0.5)
        for i in range(width):
            for j in range(height):
                self.assertEqual(gray_image.data[j, i], expected)
                self.assertEqual(bgr_image.data[j, i][0], expected)
                self.assertEqual(bgr_image.data[j, i][1], expected)

    # ------------------------------------------------------------------------------------------------------------------
    def test_grayscale_blue(self) -> None:
        """
        Test conversion from BGR to grayscale with blue channel.
        """
        red_image = Image.empty_color_image(5, 10, (255, 0, 0))
        gray_image = red_image.color_bgr2gray()
        bgr_image = gray_image.color_gray2bgr()

        width, height = gray_image.size
        expected = int(0.1140 * 255 + 0.5)
        for i in range(width):
            for j in range(height):
                self.assertEqual(gray_image.data[j, i], expected)
                self.assertEqual(bgr_image.data[j, i][0], expected)
                self.assertEqual(bgr_image.data[j, i][1], expected)
                self.assertEqual(bgr_image.data[j, i][2], expected)
                self.assertEqual(bgr_image.data[j, i][2], expected)

    # ------------------------------------------------------------------------------------------------------------------
