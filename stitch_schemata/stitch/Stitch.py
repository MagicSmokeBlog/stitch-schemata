import math
import os
import re
from pathlib import Path
from typing import List

import cv2 as cv
import img2pdf
import numpy as np
import PIL
from cleo.ui.table import Table

from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.StitchError import StitchError
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.ScanMetadata import ScanMetadata
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

        grayscale_images = []
        metadata = []
        for index, path_src in enumerate(paths):
            path_dest = self._config.tmp_path / f'page-{index}.png'

            self._io.log_notice(f'Preprocessing image <fso>{path_src}</fso>.')

            message = f'Converting <fso>{path_src}</fso> to grayscale <fso>{path_dest.relative_to(os.getcwd())}</fso>.'
            self._io.log_verbose(message)

            image = Image.read(path_src)
            image = image.grayscale()
            image.write(path_dest)

            grayscale_images.append(path_dest)

            if index == 0:
                metadata.append(ScanMetadata(path=path_src,
                                             width=image.width,
                                             height=image.height))
            else:
                meta = self._pre_stitch_image(index, paths, grayscale_images)
                metadata.append(meta)

        return metadata

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image(self, index: int, pages: List[Path], grayscale_images: List[Path]) -> ScanMetadata:
        """
        Collects metadata for stitching a scanned image.
        """
        angle = 0.0
        iteration = 0
        while True:
            extractor = TileExtractor(self._io,
                                      self._config,
                                      grayscale_images[index],
                                      self._config.tile_hints.get(pages[index].name))
            tile_top, tile_bottom = extractor.extract_tiles()

            image: Image = Image.read(grayscale_images[index - 1])
            finder = TileFinder(self._io, self._config, image)
            tile_top_match = finder.find_tile(tile_top)
            tile_bottom_match = finder.find_tile(tile_bottom)

            if tile_top_match.match < self._config.tile_match_min:
                raise StitchError(
                        f'Unable to find top tile from image {grayscale_images[index]} in image {grayscale_images[index - 1]}.')
            if tile_bottom_match.match < self._config.tile_match_min:
                raise StitchError(
                        f'Unable to find bottom tile from image {grayscale_images[index]} in image {grayscale_images[index - 1]}.')

            angle_delta = math.atan2(tile_bottom_match.y - tile_top_match.y, tile_bottom_match.x - tile_top_match.x) - \
                          math.atan2(tile_bottom.y - tile_top.y, tile_bottom.x - tile_top.x)

            if abs(angle_delta) < math.atan2(1.0, float(max(image.size()) // 2)) or \
                    iteration == (self._config.tile_iterations_max - 1):
                break

            angle -= math.degrees(angle_delta)
            image = Image.read(pages[index])
            image = image.grayscale()
            image = image.rotate(angle)
            image.write(grayscale_images[index])

            self._io.log_verbose(f'Rotation {angle}.')

            iteration += 1

        if tile_top and tile_top_match:
            return ScanMetadata(path=pages[index],
                                rotate=angle,
                                translate_x=tile_top_match.x - tile_top.x,
                                translate_y=tile_top_match.y - tile_top.y,
                                width=extractor.width,
                                height=extractor.height)

        raise ValueError('Unable to find a tile match.')

    # ------------------------------------------------------------------------------------------------------------------
    def _stitch_images(self, pages: List[ScanMetadata]) -> Image:
        """
        Stitches scanned images.

        :param pages: The metadata of the scanned images.
        """
        self._io.text('')
        self._io.title('Stitching Images')

        offset_y = 0
        offset_y0 = 0
        for page in pages:
            offset_y += page.translate_y
            if offset_y < 0:
                offset_y0 = offset_y

        total_width = 0
        total_height = 0
        offset_x = 0
        offset_y = -offset_y0
        for page in pages:
            offset_x += page.translate_x
            offset_y += page.translate_y
            total_width = offset_x + page.width
            total_height = max(total_height, offset_y + page.height)

        stitch_data = np.full((total_height, total_width, 3), (255, 255, 255), np.uint8)

        offset_x = 0
        offset_y = 0
        for index, page in enumerate(pages):
            self._io.log_notice(f'Processing image <fso>{page.path}</fso>.')

            offset_x += page.translate_x
            offset_y += page.translate_y

            if index == 0:
                overlap_x = 0
            else:
                overlap_x = self._config.margin + self._config.tile_width // 2

            image = Image.read(page.path)
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
            image.write(self._config.output_path, [cv.IMWRITE_PNG_COMPRESSION, 9])

        elif re.match(r'.*\.je?pg$', str(self._config.output_path), re.IGNORECASE):
            image.write(self._config.output_path, [cv.IMWRITE_JPEG_QUALITY, self._config.quality])

        elif re.match(r'.*\.pdf$', str(self._config.output_path), re.IGNORECASE):
            PIL.Image.MAX_IMAGE_PIXELS = image.width * image.height

            if self._config.quality == 100:
                temp_filename = self._config.tmp_path / 'stitched.png'
                image.write(temp_filename, [cv.IMWRITE_PNG_COMPRESSION, 9])
            else:
                temp_filename = self._config.tmp_path / 'stitched.jpg'
                image.write(temp_filename, [cv.IMWRITE_JPEG_QUALITY, self._config.quality])
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

# ----------------------------------------------------------------------------------------------------------------------
