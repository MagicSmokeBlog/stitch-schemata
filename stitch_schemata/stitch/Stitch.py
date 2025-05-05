import math
import re
from pathlib import Path
from typing import List

import cv2
import img2pdf
import numpy as np
import PIL
from cleo.ui.table import Table

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.OrientationDetector import OrientationDetector
from stitch_schemata.stitch.ScanMetadata import ScanMetadata
from stitch_schemata.stitch.StitchError import StitchError
from stitch_schemata.stitch.Tile import Tile
from stitch_schemata.stitch.TileExtractor import TileExtractor
from stitch_schemata.stitch.TileFinder import TileFinder


class Stitch:
    """
    Class for stitching scanned images.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: StitchSchemataIO, config: Config):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        """

        self._io: StitchSchemataIO = io
        """
        The Output decorator.
        """

        self._config: Config = config
        """
        The configuration.
        """

        self._original_images: List[Image] = []
        """
        The original scanned images.
        """

        self._grayscale_images: List[Image] = []
        """
        The grayscale images of the scanned pages.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def stitch(self, images: List[Path]) -> None:
        """
        Stitch scanned images.

        :param images: The scanned images.
        """
        metadata = self._pre_stitch_images(images)
        self._log_metadata(metadata)
        image = self._stitch_images(metadata)
        image = self._crop_stitched_image(image, metadata)
        self._save_stitched_image(image)

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_images(self, paths: List[Path]) -> List[ScanMetadata]:
        """
        Collects metadata for stitching a scanned images.

        :param paths: The paths to the scanned images.
        """
        self._io.title('Preprocessing Images')

        self._original_images = []
        self._grayscale_images = []
        metadata = []
        for index, path_src in enumerate(paths):
            self._io.log_notice(f'Preprocessing image <fso>{path_src}</fso>.')

            image = Image.read(path_src)
            self._original_images.append(image)
            self._grayscale_images.append(image.grayscale())

            if index == 0:
                meta = self._pre_stitch_image0(paths[index])
            else:
                meta = self._pre_stitch_image(index, paths)
            metadata.append(meta)

        return metadata

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image0(self, path: Path) -> ScanMetadata:
        """
        Finds the rotation of the first scanned page.
        """
        detector = OrientationDetector(self._grayscale_images[0])
        angle = detector.detect_orientation()

        if angle is None:
            self._io.log_verbose(f'Unable to find orientation of image <fso>{path}</fso>')

            return ScanMetadata(path=path,
                                rotate=0.0,
                                translate_x=0,
                                translate_y=0,
                                width=self._grayscale_images[0].width,
                                height=self._grayscale_images[0].height)

        self._grayscale_images[0] = self._original_images[0].grayscale().rotate(angle)

        return ScanMetadata(path=path,
                            rotate=angle,
                            translate_x=0,
                            translate_y=0,
                            width=self._grayscale_images[0].width,
                            height=self._grayscale_images[0].height)

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image(self, index: int, pages: List[Path]) -> ScanMetadata:
        """
        Collects metadata for stitching a scanned image.
        """
        angle = 0.0
        iteration = 0
        while True:
            extractor = TileExtractor(self._io,
                                      self._config,
                                      pages[index],
                                      self._grayscale_images[index],
                                      self._config.tile_hints.get(pages[index].name))
            tile_top, tile_bottom = extractor.extract_tiles()

            finder = TileFinder(self._io, self._config, self._grayscale_images[index - 1])
            tile_top_match = finder.find_tile(tile_top)
            tile_bottom_match = finder.find_tile(tile_bottom)

            if self._io.is_debug():
                self.__save_pages_debug(index, iteration, 'src', tile_top, tile_bottom)
                self.__save_pages_debug(index, iteration, 'dst', tile_top_match, tile_bottom_match)

            if tile_top_match.match < self._config.tile_match_min:
                raise StitchError(f'Unable to find top tile from image {pages[index]} in image {pages[index - 1]}.')
            if tile_bottom_match.match < self._config.tile_match_min:
                raise StitchError(f'Unable to find bottom tile from image {pages[index]} in image {pages[index - 1]}.')

            angle_delta = math.atan2(tile_bottom_match.y - tile_top_match.y, tile_bottom_match.x - tile_top_match.x) - \
                          math.atan2(tile_bottom.y - tile_top.y, tile_bottom.x - tile_top.x)

            if abs(angle_delta) < math.atan2(1.0, float(max(self._grayscale_images[index].size()) // 2)) or \
                    iteration == (self._config.tile_iterations_max - 1):
                break

            angle -= math.degrees(angle_delta)
            self._grayscale_images[index] = self._original_images[index].grayscale().rotate(angle)

            self._io.log_verbose(f'Rotation {angle}.')

            iteration += 1

        if tile_top and tile_top_match:
            return ScanMetadata(path=pages[index],
                                rotate=angle,
                                translate_x=tile_top_match.x - tile_top.x,
                                translate_y=tile_top_match.y - tile_top.y,
                                width=self._grayscale_images[index].width,
                                height=self._grayscale_images[index].height)

        raise StitchError(f"Unable to find a tile match in '{pages[index]}'.")

    # ------------------------------------------------------------------------------------------------------------------
    def _stitch_images(self, metadata: List[ScanMetadata]) -> Image:
        """
        Stitches scanned images.

        :param metadata: The metadata of the scanned images.
        """
        self._io.text('')
        self._io.title('Stitching Images')

        offset_y = 0
        offset_y0 = 0
        for page in metadata:
            offset_y += page.translate_y
            if offset_y < 0:
                offset_y0 = offset_y

        total_width = 0
        total_height = 0
        offset_x = 0
        offset_y = -offset_y0
        for page in metadata:
            offset_x += page.translate_x
            offset_y += page.translate_y
            total_width = offset_x + page.width
            total_height = max(total_height, offset_y + page.height)

        stitch_data = np.full((total_height, total_width, 3), (255, 255, 255), np.uint8)

        offset_x = 0
        offset_y = 0
        for index, page in enumerate(metadata):
            self._io.log_notice(f'Processing image <fso>{page.path}</fso>.')

            offset_x += page.translate_x
            offset_y += page.translate_y

            if index == 0:
                overlap_x = 0
            else:
                overlap_x = self._config.margin + self._config.tile_width // 2

            image = self._original_images[index]
            if page.rotate != 0.0:
                image = image.rotate(page.rotate)
            stitch_data = Image.merge_data(stitch_data, image.data, offset_x, offset_y, overlap_x)

        return Image(stitch_data)

    # ------------------------------------------------------------------------------------------------------------------
    def _crop_stitched_image(self, image: Image, pages: List[ScanMetadata]) -> Image:
        """
        Cops the stitches image if required.

        :param pages: The metadata of the scanned images.
        :param image: The stitched image.
        """
        if not self._config.crop:
            return image

        start = 0
        offset_y = 0
        stop = image.height
        for page in pages:
            offset_y += page.translate_y
            start = max(start, offset_y)
            stop = min(stop, page.height + offset_y)

        return Image(data=image.data[start:stop])

    # ------------------------------------------------------------------------------------------------------------------
    def _save_stitched_image(self, image: Image) -> None:
        """
        Saves the stitched image.

        :param image: The stitched image.
        """
        self._io.text('')
        self._io.title('Saving Image')

        if re.match(r'.*\.png$', str(self._config.output_path), re.IGNORECASE):
            image.write(self._config.output_path, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        elif re.match(r'.*\.je?pg$', str(self._config.output_path), re.IGNORECASE):
            image.write(self._config.output_path, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality])

        elif re.match(r'.*\.pdf$', str(self._config.output_path), re.IGNORECASE):
            PIL.Image.MAX_IMAGE_PIXELS = image.width * image.height

            if self._config.quality == 100:
                temp_filename = self._config.tmp_path / 'stitched.png'
                image.write(temp_filename, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:
                temp_filename = self._config.tmp_path / 'stitched.jpg'
                image.write(temp_filename, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality])
            with open(str(self._config.output_path), 'wb') as handle:
                handle.write(img2pdf.convert(temp_filename))
        else:
            raise StitchError(f"Unable to save stitched image as '{self._config.output_path}'.")

        self._io.text(f'Saved stitched image as <fso>{self._config.output_path}</fso>.')

    # ------------------------------------------------------------------------------------------------------------------
    def _log_metadata(self, pages: List[ScanMetadata]):
        """
        Log the metadata is nice table.

        :param pages: The metadata of the scanned images.
        """
        table = Table(self._io)

        headers = ['file', 'rotation', 'translate x', 'translate y']
        rows = []
        for page in pages:
            rows.append([str(page.path),
                         f'{page.rotate:.4f}',
                         str(page.translate_x),
                         str(page.translate_y)])

        self._io.text('')
        table.set_headers(headers)
        table.set_rows(rows)
        table.render()

    # ------------------------------------------------------------------------------------------------------------------
    def __save_pages_debug(self, index: int, iteration: int, name: str, tile_top: Tile, tile_bottom: Tile) -> None:
        """
        Save pages for debugging purposes.

        :param index: The index of the page.
        :param iteration: The iteration of fining the titles.
        :param name: Either 'src' or 'dst'.
        :param tile_top: The top tile.
        :param tile_bottom: The bottom tile.
        """
        title_color = (0, 0, 255)
        area_color = (0, 255, 0)
        width = 2

        if name == 'src':
            path = self._config.tmp_path / f'page-{index}-iteration-{iteration}-page{index}.png'
            image = self._grayscale_images[index].data.copy()
            areas = [((self._config.margin, self._config.margin),
                      (int(self._config.overlap_min * self._grayscale_images[index].width - 1),
                       self._grayscale_images[index].height - self._config.margin - 1))]
        else:
            path = self._config.tmp_path / f'page-{index}-iteration-{iteration}-page{index - 1}.png'
            image = self._grayscale_images[index - 1].data.copy()
            areas = [((0, max(0, tile_top.y - self._config.vertical_offset_max)),
                      (self._grayscale_images[index - 1].width - 1,
                       min(self._grayscale_images[index - 1].height - 1,
                           tile_top.y + tile_top.image.height + self._config.vertical_offset_max - 1))),
                     ((0, max(0, tile_bottom.y - self._config.vertical_offset_max)),
                      (self._grayscale_images[index - 1].width - 1,
                       min(self._grayscale_images[index - 1].height - 1,
                           tile_bottom.y + tile_bottom.image.height + self._config.vertical_offset_max - 1)))]

        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        for area in areas:
            cv2.rectangle(image, area[0], area[1], area_color, width)
        cv2.rectangle(image,
                      (tile_top.x, tile_top.y),
                      (tile_top.x + self._config.tile_width, tile_top.y + self._config.tile_height),
                      title_color,
                      width)
        cv2.rectangle(image,
                      (tile_bottom.x, tile_bottom.y),
                      (tile_bottom.x + self._config.tile_width, tile_bottom.y + self._config.tile_height),
                      title_color,
                      width)
        cv2.imwrite(str(path), image)

# ----------------------------------------------------------------------------------------------------------------------
