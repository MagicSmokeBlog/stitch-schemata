import math
import re
from pathlib import Path
from typing import Any, List, Tuple

import cv2
import img2pdf
import numpy as np
import pikepdf
import PIL
from cleo.ui.table import Table
from PIL import Image as PilImage

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.ocr.Config import Config as OcrConfig
from stitch_schemata.ocr.Ocr import Ocr
from stitch_schemata.stitch.Config import Config
from stitch_schemata.stitch.Image import Image
from stitch_schemata.stitch.OrientationDetector import OrientationDetector
from stitch_schemata.stitch.ScanMetadata import ScanMetadata
from stitch_schemata.stitch.Side import Side
from stitch_schemata.stitch.StitchError import StitchError
from stitch_schemata.stitch.Tile import Tile
from stitch_schemata.stitch.TileExtractor import TileExtractor
from stitch_schemata.stitch.TileFinder import TileFinder


class Stitch:
    """
    Class for stitching scanned images.
    """
    _debug_seq: int = 0
    """
    Sequence number for saving images in debug mode.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: StitchSchemataIO, config: Config, paths: List[Path]):
        """
        Object constructor.

        :param io:The Output decorator.
        :param config: The configuration.
        :param paths: The paths to the scanned images.
        """
        self._io: StitchSchemataIO = io
        """
        The Output decorator.
        """

        self._config: Config = config
        """
        The configuration.
        """

        self._paths: List[Path] = paths
        """
        The paths to the scanned images.
        """

        self._metadata: List[ScanMetadata] = []
        """
        The metadata of the scanned images.
        """

        self._original_images: List[Image] = []
        """
        The original scanned images.
        """

        self._grayscale_images: List[Image] = []
        """
        The grayscale images of the scanned pages.
        """

        self._stitched_image: Image | None = None
        """
        The stitched image.
        """

        self._ocr_pdf: pikepdf.Pdf | None = None
        """
        The PDF page with hidden OCR text.
        """

    # ------------------------------------------------------------------------------------------------------------------
    def stitch(self) -> None:
        """
        Stitch scanned images.
        """
        self._pre_stitch_images()
        self._log_metadata()
        self._stitch_images()
        self._crop_stitched_image()
        self._debug_mark_stitches()
        self._ocr()
        self._save_stitched_image()

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_images(self) -> None:
        """
        Collects metadata for stitching scanned images.
        """
        self._io.text('')
        self._io.title('Preprocessing Images')

        self._original_images = []
        self._grayscale_images = []
        self._metadata = []
        for index, path_src in enumerate(self._paths):
            self._io.log_notice(f'Preprocessing image <fso>{path_src}</fso>.')

            image = Image.read(path_src)
            self._original_images.append(image)
            self._grayscale_images.append(image.grayscale())

            if index == 0:
                meta = self._pre_stitch_image0()
            else:
                meta = self._pre_stitch_image(index)
            self._metadata.append(meta)

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image0(self) -> ScanMetadata:
        """
        Finds the rotation of the first scanned image.
        """
        detector = OrientationDetector(self._grayscale_images[0])
        angle = detector.detect_orientation()

        if angle is None:
            self._io.log_verbose(f'Unable to find orientation of image <fso>{self._paths[0]}</fso>.')

            return ScanMetadata(rotate=0.0,
                                translate_x=0,
                                translate_y=0,
                                width=self._grayscale_images[0].width,
                                height=self._grayscale_images[0].height)

        if abs(angle) > self._config.rotation_max:
            self._io.log_verbose(f'Ignoring found rotation offset of {angle:.4f} of image <fso>{self._paths[0]}</fso>.')

            return ScanMetadata(rotate=0.0,
                                translate_x=0,
                                translate_y=0,
                                width=self._grayscale_images[0].width,
                                height=self._grayscale_images[0].height)

        self._grayscale_images[0] = self._original_images[0].grayscale().rotate(angle)

        return ScanMetadata(rotate=angle,
                            translate_x=0,
                            translate_y=0,
                            width=self._grayscale_images[0].width,
                            height=self._grayscale_images[0].height)

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image(self, index: int) -> ScanMetadata:
        """
        Collects metadata for stitching a scanned image.

        :param index: The index of the scanned image to stitch.
        """
        try:
            return self._pre_stitch_image_helper(index,
                                                 index,
                                                 index - 1,
                                                 Side.LEFT,
                                                 1,
                                                 self._config.tile_hints.get(self._paths[index].name))
        except StitchError as error:
            self._io.log_verbose(str(error))
            return self._pre_stitch_image_helper(index,
                                                 index - 1,
                                                 index,
                                                 Side.RIGHT,
                                                 -1,
                                                 None)

    # ------------------------------------------------------------------------------------------------------------------
    def _pre_stitch_image_helper(self,
                                 index: int,
                                 index_extract: int,
                                 index_matched: int,
                                 side: Side,
                                 sign: int,
                                 tile_hints: Tuple[Tuple[int, int], Tuple[int, int]] | None) -> ScanMetadata:
        """
        Collects metadata for stitching a scanned image.

        :param index: The index of the scanned image to stitch.
        :param index_extract: The index of the image of which tiles must be extracted.
        :param index_matched: The index of the image of which tiles must be matched.
        :param side: The side of the image at which tile must be extracted.
        :param sign: The sign for involved match from right to left vs left to right.
        :param tile_hints: The tile hints.
        """
        self._io.log_verbose(f'Extracting tiles from image {self._paths[index_extract]} and matching in image '
                             f'{self._paths[index_matched]}.')

        angle = 0.0
        angle_delta = 0.0
        tile_top = None
        tile_top_match = None
        for iteration in range(self._config.tile_iterations_max):
            angle -= angle_delta

            if angle > self._config.rotation_max:
                raise StitchError(f'Found rotation offset {angle:.4f} of image <fso>{self._paths[index]}</fso> '
                                  f'exceeds maximum rotation angle of {self._config.rotation_max}.')

            self._grayscale_images[index] = self._original_images[index].grayscale().rotate(angle)

            extractor = TileExtractor(self._io,
                                      self._config,
                                      self._paths[index_extract],
                                      side,
                                      self._grayscale_images[index_extract],
                                      tile_hints)
            tile_top, tile_bottom, area = extractor.extract_tiles()

            finder = TileFinder(self._io, self._config, self._grayscale_images[index_matched])
            tile_top_match = finder.find_tile(tile_top)
            tile_bottom_match = finder.find_tile(tile_bottom)

            if self._io.is_debug():
                self._debug_save_page_extract(iteration,
                                              index_extract, tile_top, tile_bottom, area)
                self._debug_save_page_matched(iteration,
                                              index_extract, tile_top, tile_bottom,
                                              index_matched, tile_top_match, tile_bottom_match)

            if tile_top_match.match < self._config.tile_match_min:
                raise StitchError(f'Unable to find top tile from image {self._paths[index_extract]} '
                                  f'in image {self._paths[index_matched]}.')
            if tile_bottom_match.match < self._config.tile_match_min:
                raise StitchError(f'Unable to find bottom tile from image {self._paths[index_extract]} '
                                  f'in image {self._paths[index_matched]}.')

            angle_delta = math.atan2(tile_bottom_match.y - tile_top_match.y, tile_bottom_match.x - tile_top_match.x) - \
                          math.atan2(tile_bottom.y - tile_top.y, tile_bottom.x - tile_top.x)
            angle_delta = math.degrees(sign * angle_delta)

            if not self._original_images[index].rotation_has_effect(angle_delta):
                break

            self._io.log_verbose(f'Rotation {angle}.')

        if tile_top and tile_top_match:
            return ScanMetadata(rotate=angle,
                                translate_x=sign * (tile_top_match.x - tile_top.x),
                                translate_y=sign * (tile_top_match.y - tile_top.y),
                                width=self._grayscale_images[index].width,
                                height=self._grayscale_images[index].height)

        raise StitchError(f"Unable to find a tile match in '{self._paths[index]}'.")

    # ------------------------------------------------------------------------------------------------------------------
    def _stitch_images(self) -> None:
        """
        Stitches scanned images.
        """
        self._io.text('')
        self._io.title('Stitching Images')

        offset_y = 0
        offset_y0 = 0
        for page in self._metadata:
            offset_y += page.translate_y
            if offset_y < 0:
                offset_y0 = offset_y

        total_width = 0
        total_height = 0
        offset_x = 0
        offset_y = -offset_y0
        for page in self._metadata:
            offset_x += page.translate_x
            offset_y += page.translate_y
            total_width = offset_x + page.width
            total_height = max(total_height, offset_y + page.height)

        stitch_data = np.full((total_height, total_width, 3), (255, 255, 255), np.uint8)

        offset_x = 0
        offset_y = 0
        for index, page in enumerate(self._metadata):
            self._io.log_notice(f'Processing image <fso>{self._paths[index]}</fso>.')

            offset_x += page.translate_x
            offset_y += page.translate_y

            if index == 0:
                overlap_x = 0
            else:
                overlap_x = self._config.margin + self._config.tile_width // 2

            image = self._original_images[index].rotate(page.rotate)
            stitch_data = Image.merge_data(stitch_data, image.data, offset_x, offset_y, overlap_x)

        self._stitched_image = Image(stitch_data)

    # ------------------------------------------------------------------------------------------------------------------
    def _crop_stitched_image(self) -> None:
        """
        Crops the stitches image if required.
        """
        if not self._config.crop:
            return

        start = 0
        offset_y = 0
        stop = self._stitched_image.height
        for page in self._metadata:
            offset_y += page.translate_y
            start = max(start, offset_y)
            stop = min(stop, page.height + offset_y)

        self._stitched_image = Image(data=self._stitched_image.data[start:stop])

    # ------------------------------------------------------------------------------------------------------------------
    def _save_stitched_image(self) -> None:
        """
        Saves the stitched image.
        """
        if str(self._config.output_path).lower().endswith('.pdf') and self._config.ocr:
            return

        self._io.text('')
        self._io.title('Saving Image')

        if str(self._config.output_path).lower().endswith('.png'):
            self._stitched_image.write(self._config.output_path, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        elif re.match(r'.*\.je?pg$', str(self._config.output_path), re.IGNORECASE):
            self._stitched_image.write(self._config.output_path, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality])

        elif str(self._config.output_path).lower().endswith('.pdf'):
            PIL.Image.MAX_IMAGE_PIXELS = self._stitched_image.width * self._stitched_image.height

            if self._config.quality == 100:
                temp_filename = self._config.tmp_path / 'stitched.png'
                self._stitched_image.write(temp_filename, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:
                temp_filename = self._config.tmp_path / 'stitched.jpg'
                self._stitched_image.write(temp_filename, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality])

            with open(str(self._config.output_path), 'wb') as handle:
                dpi = self._config.dpi
                handle.write(img2pdf.convert(temp_filename,
                                             pdfa=self._extract_icc_profile(),
                                             layout_fun=img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))))
        else:
            raise StitchError(f"Unable to save stitched image as '{self._config.output_path}'.")

        self._io.text(f'Saved stitched image as <fso>{self._config.output_path}</fso>.')

    # ------------------------------------------------------------------------------------------------------------------
    def _log_metadata(self):
        """
        Logs the metadata of the scanned images in nice table.
        """
        table = Table(self._io)

        headers = ['file', 'rotation', 'translate x', 'translate y']
        rows = []

        for index, page in enumerate(self._metadata):
            rows.append([str(self._paths[index]),
                         f'{page.rotate:.4f}',
                         str(page.translate_x),
                         str(page.translate_y)])

        self._io.text('')
        table.set_headers(headers)
        table.set_rows(rows)
        table.render()

    # ------------------------------------------------------------------------------------------------------------------
    def _debug_save_page_extract(self,
                                 iteration: int,
                                 index_extract: int,
                                 tile_top: Tile,
                                 tile_bottom: Tile,
                                 area: Any) -> None:
        """
        Saves a scanned pages with extracted tiles for debugging purposes.

        :param iteration: The iteration of fining the titles.
        :param index_extract: The index of the page.
        :param tile_top: The top tile.
        :param tile_bottom: The bottom tile.
        """
        title_color = (0, 0, 255)
        area_color = (0, 255, 0)
        width = 2

        path = self._config.tmp_path / f'{self._debug_seq_value():02d}-page-{index_extract}-iteration-{iteration}-page{index_extract}.png'
        image = self._grayscale_images[index_extract].data.copy()

        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if area is not None:
            cv2.rectangle(image, area[0], area[1], area_color, width)
        cv2.rectangle(image,
                      (tile_top.x, tile_top.y),
                      (tile_top.x + tile_top.image.width - 1,
                       tile_top.y + tile_top.image.height - 1),
                      title_color,
                      width)
        cv2.rectangle(image,
                      (tile_bottom.x, tile_bottom.y),
                      (tile_bottom.x + tile_bottom.image.width - 1,
                       tile_bottom.y + tile_bottom.image.height - 1),
                      title_color,
                      width)
        cv2.imwrite(str(path), image)

    # ------------------------------------------------------------------------------------------------------------------
    def _debug_save_page_matched(self,
                                 iteration: int,
                                 index_extract: int,
                                 tile_top: Tile,
                                 tile_bottom: Tile,
                                 index_matched: int,
                                 tile_top_match: Tile,
                                 tile_bottom_match: Tile) -> None:
        """
        Saves scanned page with matched tile for debugging purposes.

        :param iteration: The iteration of fining the titles.
        :param index_extract: The index of the page.
        :param tile_top: The top tile.
        :param tile_bottom: The bottom tile.
        :param tile_top_match: The top matched tile.
        :param tile_bottom_match: The bottom matched tile.
        """
        title_color = (0, 0, 255)
        area_color = (0, 255, 0)
        width = 2

        path = self._config.tmp_path / f'{self._debug_seq_value():02d}-page-{index_extract}-iteration-{iteration}-page{index_matched}.png'
        image = self._grayscale_images[index_matched].data.copy()
        areas = [((0, max(0, tile_top.y - self._config.vertical_offset_max)),
                  (self._grayscale_images[index_matched].width - 1,
                   min(self._grayscale_images[index_matched].height - 1,
                       tile_top.y + tile_top.image.height + self._config.vertical_offset_max - 1))),
                 ((0, max(0, tile_bottom.y - self._config.vertical_offset_max)),
                  (self._grayscale_images[index_matched].width - 1,
                   min(self._grayscale_images[index_matched].height - 1,
                       tile_bottom.y + tile_bottom.image.height + self._config.vertical_offset_max - 1)))]

        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        for area in areas:
            cv2.rectangle(image, area[0], area[1], area_color, width)
        cv2.rectangle(image,
                      (tile_top_match.x, tile_top_match.y),
                      (tile_top_match.x + tile_top_match.image.width - 1,
                       tile_top_match.y + tile_top_match.image.height - 1),
                      title_color,
                      width)
        cv2.rectangle(image,
                      (tile_bottom_match.x, tile_bottom_match.y),
                      (tile_bottom_match.x + tile_bottom_match.image.width - 1,
                       tile_bottom_match.y + tile_bottom_match.image.height - 1),
                      title_color,
                      width)
        cv2.imwrite(str(path), image)

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_icc_profile(self) -> str:
        """
        Extracts the color profile from the scanned images.
        """
        icc = PilImage.open(self._paths[0]).info.get('icc_profile')
        if icc is not None:
            path = self._config.tmp_path / 'color-profile.icc'
            with open('cp.icc', 'wb') as handle:
                handle.write(icc)
        else:
            path = Path(__file__).resolve().parent.parent / 'data/sRGB2014.icc'

        return str(path)

    # ------------------------------------------------------------------------------------------------------------------
    def _debug_seq_value(self) -> int:
        """
        """
        value = self._debug_seq
        self._debug_seq += 1

        return value

    # ------------------------------------------------------------------------------------------------------------------
    def _debug_mark_stitches(self) -> None:
        """
        Adds markers at the stitches in the stitched image.
        """
        if not self._io.is_debug():
            return

        marker_color = (0, 0, 255)
        alpha = 0.5
        height = self._stitched_image.height
        data = self._stitched_image.data
        overlay = data.copy()
        overlap_x = self._config.margin + self._config.tile_width // 2

        offset = 0
        for page in self._metadata[1:]:
            offset += page.translate_x
            start = (offset + overlap_x - 1, 0)
            end = (offset + overlap_x, height - 1)
            cv2.rectangle(overlay, start, end, marker_color, thickness=1)

        self._stitched_image = Image(cv2.addWeighted(overlay, alpha, data, 1.0 - alpha, 0.0))

    # ------------------------------------------------------------------------------------------------------------------
    def _ocr(self) -> None:
        """
        Adds OCR to the stitched image.
        """
        if not self._config.ocr or not str(self._config.output_path).lower().endswith('.pdf'):
            return

        config = OcrConfig(dpi=self._config.dpi,
                           tmp_path=self._config.tmp_path,
                           input_path=None,
                           output_path=self._config.output_path,
                           quality=self._config.quality,
                           ocr_psm=self._config.ocr_psm,
                           ocr_language=self._config.ocr_language,
                           ocr_confidence_min=self._config.ocr_confidence_min)
        ocr = Ocr(self._io, config, self._stitched_image)
        self._ocr_pdf = ocr.ocr()

# ----------------------------------------------------------------------------------------------------------------------
