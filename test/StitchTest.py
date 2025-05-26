import os
import unittest
from pathlib import Path

import cv2
from cleo.application import Application
from cleo.testers.command_tester import CommandTester

from stitch_schemata.command.StitchSchemataCommand import StitchSchemataCommand
from stitch_schemata.stitch.Image import Image


class StitchTest(unittest.TestCase):
    """
    Unit test for stitch images.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def test_stitch_without_rotation(self):
        """
        Test without rotation.
        """
        dpi = 600
        inch = 25.4
        margin = 50
        tile_width = 300
        scanner_width = int(600 * 216 / inch)

        width = int(420 * dpi / inch)
        height = int(297 * dpi / inch)

        red = (0, 0, 255)
        green = (0, 255, 0)
        gray = (240, 240, 240)

        original = Image.empty_color_image(width, height, gray)

        x = int(0.5 * original.width - 0.5 * scanner_width + margin + 0.5 * tile_width)
        y = dpi
        cv2.circle(original.data, (x, y), int(0.4 * tile_width), red, -1)
        cv2.circle(original.data, (x, original.height - y), int(0.4 * tile_width), red, -1)

        x = int(0.5 * original.width + 0.5 * scanner_width - margin - 0.5 * tile_width)
        y = 2 * dpi
        cv2.circle(original.data, (x, y), int(0.4 * tile_width), green, -1)
        cv2.circle(original.data, (x, original.height - y), int(0.4 * tile_width), green, -1)

        original.write('test/original.png')

        scan1 = original.sub_image(0, 0, scanner_width, original.height)
        scan2 = original.sub_image((original.width - scanner_width) // 2, 0, scanner_width, original.height)
        scan3 = original.sub_image(original.width - scanner_width, 0, scanner_width, original.height)

        scan1.write('test/scan1.png')
        scan2.write('test/scan2.png')
        scan3.write('test/scan3.png')

        application = Application()
        application.add(StitchSchemataCommand())

        command = application.find('stitch')
        command_tester = CommandTester(command)
        command_tester.execute('-o test/stitched.png test/scan1.png test/scan2.png test/scan3.png')

        stitched = Image.read(Path('test/stitched.png'))
        self.assertEqual(stitched.width, original.width)
        self.assertEqual(stitched.height, original.height)

        x, y, match = original.match_template(stitched)
        self.assertEqual(0, x)
        self.assertEqual(0, y)
        self.assertGreater(match, 0.99)

        os.unlink('test/original.png')
        os.unlink('test/scan1.png')
        os.unlink('test/scan2.png')
        os.unlink('test/scan3.png')
        os.unlink('test/stitched.png')

    # ------------------------------------------------------------------------------------------------------------------
    def test_stitch_with_rotation1(self):
        """
        Test with rotation.
        """
        dpi = 600
        inch = 25.4
        margin = 50
        tile_width = 300
        scanner_width = int(600 * 216 / inch)

        width = int(420 * dpi / inch)
        height = int(297 * dpi / inch)

        red = (0, 0, 255)
        green = (0, 255, 0)
        gray = (240, 240, 240)
        black = (0, 0, 0)

        original = Image.empty_color_image(width, height, gray)

        cv2.rectangle(original.data, (0, original.height // 2 - 2), (width, original.height // 2 + 2), black, -1)

        x = int(0.5 * original.width - 0.5 * scanner_width + margin + 0.5 * tile_width)
        y = dpi
        cv2.circle(original.data, (x, y), int(0.4 * tile_width), red, -1)
        cv2.circle(original.data, (x, original.height - y), int(0.4 * tile_width), red, -1)

        x = int(0.5 * original.width + 0.5 * scanner_width - margin - 0.5 * tile_width)
        y = 2 * dpi
        cv2.circle(original.data, (x, y), int(0.4 * tile_width), green, -1)
        cv2.circle(original.data, (x, original.height - y), int(0.4 * tile_width), green, -1)

        original.write('test/original.png')

        scan1 = original.sub_image(0, 0, scanner_width, original.height)
        scan2 = original.sub_image((original.width - scanner_width) // 2, 0, scanner_width, original.height)
        scan3 = original.sub_image(original.width - scanner_width, 0, scanner_width, original.height)

        scan2 = scan2.rotate(0.3333)
        scan3 = scan3.rotate(-0.5555)

        scan1.write('test/scan1.png')
        scan2.write('test/scan2.png')
        scan3.write('test/scan3.png')

        application = Application()
        application.add(StitchSchemataCommand())

        command = application.find('stitch')
        command_tester = CommandTester(command)
        command_tester.execute('-o test/stitched.png test/scan1.png test/scan2.png test/scan3.png')

        stitched = Image.read(Path('test/stitched.png'))
        self.assertGreater(stitched.width, 9852 - 5)
        self.assertGreater(stitched.height, 6843 - 5)

        x, y, match = original.match_template(stitched)
        self.assertEqual(x, 0)
        self.assertGreater(y, 84 - 5)
        self.assertGreater(match, 0.99)

        os.unlink('test/original.png')
        os.unlink('test/scan1.png')
        os.unlink('test/scan2.png')
        os.unlink('test/scan3.png')
        os.unlink('test/stitched.png')


# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
