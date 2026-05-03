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
    def test_rotation_size1(self) -> None:
        """
        Test the size of an image after rotation.
        """
        image_org = Image.empty_color_image(1000, 1000, (0, 0, 255))
        image_dest = image_org.rotate(45)
        self.assertEqual(image_dest.size, (707, 707))

    # ------------------------------------------------------------------------------------------------------------------
    def test_rotation_size2(self) -> None:
        """
        Test the size of an image after rotation.
        """
        image_org = Image.empty_color_image(1500, 500, (0, 0, 255))
        image_dest = image_org.rotate(20)
        self.assertEqual(image_dest.size, (730, 266))

    # ------------------------------------------------------------------------------------------------------------------
    def test_rotation_size3(self) -> None:
        """
        Test the size of an image after rotation.
        """
        image_org = Image.empty_color_image(4934, 6989, (0, 0, 255))
        image_dest = image_org.rotate(0.05)
        self.assertEqual(image_dest.size, (4927, 6984))

    # ------------------------------------------------------------------------------------------------------------------
    def test_rotation_has_effect(self) -> None:
        """
        Test the rotation_has_effect.
        """
        image_org = Image.empty_color_image(5000, 7000, (0, 0, 255))
        for i in range(0, 51, 2):
            angle = 0.001 * i
            image_dest = image_org.rotate(angle)
            self.assertEqual(image_org.rotation_has_effect(angle), image_org.size != image_dest.size)
            if i==0:
                self.assertFalse(image_org.rotation_has_effect(angle))
            if i==50:
                self.assertTrue(image_org.rotation_has_effect(angle))


# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
