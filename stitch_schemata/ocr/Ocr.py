import datetime
import subprocess
from csv import reader
from pathlib import Path
from typing import Any, List

import cv2
import img2pdf
import numpy as np
import pikepdf
import PIL
from cv2 import Mat
from numpy import dtype, floating, integer, ndarray, ndenumerate
from pikepdf import Matrix, Name, Rectangle
from pikepdf.canvas import Canvas, Color, Text
from PIL import Image, Image as PilImage

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.ocr.Config import Config
from stitch_schemata.ocr.GlyphlessFont import GlyphlessFont
from stitch_schemata.ocr.OcrPixels2Points import OcrPixels2Points
from stitch_schemata.ocr.OcrText import OcrText
from stitch_schemata.stitch.Image import Image


class Ocr:
    # ------------------------------------------------------------------------------------------------------------------
    GREEN = Color(0, 1, 0, 1)
    FUCHSIA = Color(1, 0, 1, 1)

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 io: StitchSchemataIO,
                 config: Config,
                 *,
                 timestamp: datetime.datetime,
                 image: Image | None = None):
        """
        Class for running tesseract on images and creating PDF files with OCR text.
        """
        self._io: StitchSchemataIO = io
        """
        The Output decorator.
        """

        self._config: Config = config
        """
        The configuration.
        """

        self._image: Image | None = image
        """
        The image on which to operate.
        """

        self._image_path: Path | None = None
        """
        The path the path to the image.
        """

        self._texts: List[OcrText] = []
        """
        The texts found by OCR.
        """

        self._pdf: pikepdf.Pdf | None = None
        """
        The generated PDF.
        """

        self._timestamp: datetime.datetime = timestamp
        """
        The timestamp of the generated PDF.
        """

        self._no_ocr = False

        if self._image is None:
            self._image_path = self._config.input_path
            self._image = Image.read(self._image_path)
        if self._image_path is None:
            self._image_path = self._config.tmp_path / 'ocr.png'
            self._image.write(self._image_path, [cv2.IMWRITE_PNG_COMPRESSION, 0])

    # ------------------------------------------------------------------------------------------------------------------
    def ocr(self):
        """
        Creates a PDF file from an image with a hidden text layer.
        """
        self._io.text('')
        self._io.title('Saving PDF')

        PIL.Image.MAX_IMAGE_PIXELS = self._image.width * self._image.height

        self._process_image()
        self._post_process_image()
        self._run_tesseract()
        self._create_pdf()
        self._save_pdf()

        self._io.text(f'Saved PDF as <fso>{self._config.output_path}</fso>.')

    # ------------------------------------------------------------------------------------------------------------------
    def _run_tesseract(self):
        """
        Runs tesseract on an image.
        """
        if self._no_ocr:
            self._texts = []
            return

        self._io.text('')
        self._io.title('OCR')

        tesseract_path = self._config.tmp_path / 'tesseract.png'
        tesseract_image = self._image.color_bgr2gray()
        tesseract_image.write(tesseract_path, [cv2.IMWRITE_PNG_COMPRESSION, 0])

        self._io.text(f'Running tesseract on <fso>{tesseract_path}</fso>.')

        tsv_path = self._config.tmp_path / tesseract_path.stem
        command = ['tesseract',
                   '--psm',
                   self._config.ocr_psm,
                   '-l',
                   self._config.ocr_language,
                   '--dpi',
                   str(self._config.dpi),
                   str(tesseract_path),
                   str(tsv_path),
                   'tsv']
        self._io.log_verbose('')
        self._io.log_verbose(f'Running: {" ".join(command)}')
        subprocess.run(command)

        self._texts = []
        tsv_path = Path(str(tsv_path) + '.tsv')
        with open(tsv_path, 'r') as csv_file:
            csv_reader = reader(csv_file, delimiter='\t', quotechar=None, escapechar=None)
            header = next(csv_reader)

            for row in csv_reader:
                row = dict(zip(header, row))
                text = OcrText(level=int(row['level']),
                               page_num=int(row['page_num']),
                               block_num=int(row['block_num']),
                               par_num=int(row['par_num']),
                               line_num=int(row['line_num']),
                               word_num=int(row['word_num']),
                               left=int(row['left']),
                               top=int(row['top']),
                               width=int(row['width']),
                               height=int(row['height']),
                               conf=float(row['conf']),
                               text=str(row['text']))

                self._texts.append(text)

    # ------------------------------------------------------------------------------------------------------------------
    def _create_pdf_canvas(self):
        """
        Creates a canvas for the hidden text layer.
        """
        width, height = self._image.size
        p2d = OcrPixels2Points(width, height, self._config.dpi)

        fontname: Name = Name("/f-0-0")
        font = GlyphlessFont()
        canvas = Canvas(page_size=(p2d.map_pixels(width), p2d.map_pixels(height)))
        canvas.add_font(fontname, font)

        return canvas, fontname, font, p2d

    # ------------------------------------------------------------------------------------------------------------------
    def _create_pdf(self) -> None:
        """
        Creates a PDF with a single page with a hidden text layer.
        """
        canvas, fontname, font, p2d = self._create_pdf_canvas()
        fontsize_default = 12.0

        with canvas.do.save_state():
            for ocr_text in self._texts:
                if ocr_text.level == 5:
                    if ocr_text.conf >= self._config.ocr_confidence_min or self._io.is_debug():
                        text_width = font.text_width(ocr_text.text, fontsize_default)
                        fontsize = fontsize_default * p2d.map_pixels(ocr_text.width) / text_width

                        x, y = p2d.map_coordinates(ocr_text.left, ocr_text.top, ocr_text.height)

                        pdf_text = Text()
                        pdf_text.font(fontname, fontsize)
                        pdf_text.render_mode(3)
                        pdf_text.text_transform(Matrix(1, 0, 0, 1, x, y))
                        pdf_text.show(font.text_encode(ocr_text.text))
                        canvas.do.draw_text(pdf_text)

                        if self._io.is_debug():
                            if ocr_text.conf >= self._config.ocr_confidence_min:
                                color = self.GREEN
                            else:
                                color = self.FUCHSIA
                            x, y, w, h = p2d.map_box(ocr_text.left, ocr_text.top, ocr_text.width, ocr_text.height)
                            canvas.do.stroke_color(color).line_width(0.1).rect(x, y, w, h, False)

        self._pdf = canvas.to_pdf()

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_icc_profile(self) -> str:
        """
        Extracts the color profile from the scanned images.
        """
        icc = PilImage.open(self._image_path).info.get('icc_profile')
        if icc is not None:
            path = self._config.tmp_path / 'color-profile.icc'
            with open('cp.icc', 'wb') as handle:
                handle.write(icc)
        else:
            path = Path(__file__).resolve().parent.parent / 'data/sRGB2014.icc'

        return str(path)

    # ------------------------------------------------------------------------------------------------------------------
    def _save_pdf(self):
        """
        Saves the image in a PDF.
        """
        if self._config.quality == 100:
            temp_filename = self._config.tmp_path / 'ocr.png'
            self._image.write(temp_filename, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        else:
            temp_filename = self._config.tmp_path / 'ocr.jpg'
            self._image.write(temp_filename, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality,
                                              cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                                              cv2.IMWRITE_JPEG_PROGRESSIVE, 1])

        filename_temp_pdf = self._config.tmp_path / 'image.pdf'
        with open(str(filename_temp_pdf), 'wb') as handle:
            dpi = self._config.dpi
            handle.write(img2pdf.convert(temp_filename,
                                         pdfa=self._extract_icc_profile(),
                                         layout_fun=img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))))

        width, height = self._image.size
        p2d = OcrPixels2Points(width, height, self._config.dpi)
        font = GlyphlessFont()
        pdf = pikepdf.Pdf.open(Path(filename_temp_pdf))
        font.register(pdf)
        pdf.pages[0].add_overlay(self._pdf.pages[0],
                                 Rectangle(0, 0, p2d.map_pixels(width), p2d.map_pixels(height)))

        with pdf.open_metadata() as meta:
            meta.mark = False
            formated_timestamp = self._timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            meta['xmp:CreateDate'] = formated_timestamp
            meta['xmp:ModifyDate'] = formated_timestamp
            meta['xmp:MetadataDate'] = formated_timestamp
            meta['xmp:CreatorTool'] = 'https://github.com/MagicSmokeBlog/stitch-schemata'

        pdf.save(self._config.output_path, min_version=('A', 4), deterministic_id=True)

    # ------------------------------------------------------------------------------------------------------------------
    def _process_image(self):
        """
        Processes the image according to the mode.
        """
        mode = self._config.mode

        if '-avg' in mode:
            mode = mode.replace('-avg', '')
            data = self._remove_average()

            self._image = Image(data)

        if '+diaper-duty' in mode:
            mode = mode.replace('+diaper-duty', '')
            self._diaper_duty()

        if '+darken' in mode:
            mode = mode.replace('+darken', '')
            darken = True
        else:
            darken = False

        if '-ocr' in mode:
            mode = mode.replace('-ocr', '')
            self._no_ocr = True

        if mode == 'color':
            pass

        elif mode == 'color+filter':
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))

        elif mode == 'gs+filter':
            self._image = self._image.color_bgr2gray()
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))

        elif mode == 'bgw+filter':
            self._image = self._image.color_bgr2gray()
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            for index, value in ndenumerate(self._image.data):
                value = self._image.data[index]
                if value <= 127:
                    new_value = 33  # 212121
                elif value <= 171:
                    new_value = 127
                else:
                    new_value = 255
                self._image.data[index] = new_value

        elif mode == 'bgw+p':
            grayscale = self._image.color_bgr2gray()
            for index, value in ndenumerate(grayscale.data):
                value = grayscale.data[index]
                if value <= 127:
                    new_value = 33  # 212121
                elif value <= 171:
                    new_value = 127
                else:
                    new_value = 255
                grayscale.data[index] = new_value
            grayscale = grayscale.color_gray2bgr()

            self._pronounced_colors(grayscale)

        elif mode == 'bgw+p+filter':
            grayscale = self._image.color_bgr2gray()
            grayscale = Image(cv2.bilateralFilter(grayscale.data, 3, 64, 64))
            for index, value in ndenumerate(grayscale.data):
                value = grayscale.data[index]
                if value <= 127:
                    new_value = 33  # 212121
                elif value <= 171:
                    new_value = 127
                else:
                    new_value = 255
                grayscale.data[index] = new_value
            grayscale = grayscale.color_gray2bgr()

            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            self._pronounced_colors(grayscale)

        elif mode == 'bggw+filter':
            self._image = self._image.color_bgr2gray()
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            for index, value in ndenumerate(self._image.data):
                value = self._image.data[index]
                if value <= 127:
                    new_value = 33  # 212121
                elif value <= 170:
                    new_value = 127
                elif value <= 213:
                    new_value = 170
                else:
                    new_value = 255
                self._image.data[index] = new_value

        elif mode == 'hgs':
            self._image = self._image.color_bgr2gray()
            for index, value in ndenumerate(self._image.data):
                if self._image.data[index] >= 128:
                    self._image.data[index] = 255
                elif self._image.data[index] < 33:  # 212121
                    self._image.data[index] = 33

        elif mode == 'hgs+filter':
            self._image = self._image.color_bgr2gray()
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            for index, value in ndenumerate(self._image.data):
                if self._image.data[index] >= 128:
                    self._image.data[index] = 255
                elif self._image.data[index] < 33:  # 212121
                    self._image.data[index] = 33

        elif mode == 'hgs+p':
            grayscale = self._image.color_bgr2gray()
            for index, value in ndenumerate(grayscale.data):
                if grayscale.data[index] >= 128:
                    grayscale.data[index] = 255
                elif grayscale.data[index] < 33:  # 212121
                    grayscale.data[index] = 33
            grayscale = grayscale.color_gray2bgr()

            self._pronounced_colors(grayscale)

        elif mode == 'hgs+p+filter':
            grayscale = self._image.color_bgr2gray()
            grayscale = Image(cv2.bilateralFilter(grayscale.data, 3, 64, 64))
            for index, value in ndenumerate(grayscale.data):
                if grayscale.data[index] >= 128:
                    grayscale.data[index] = 255
                elif grayscale.data[index] < 33:  # 212121
                    grayscale.data[index] = 33
            grayscale = grayscale.color_gray2bgr()

            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            self._pronounced_colors(grayscale)


        elif mode == 'qgs':
            self._image = self._image.color_bgr2gray()
            for index, value in ndenumerate(self._image.data):
                if self._image.data[index] >= 192:  # B0B0B0
                    self._image.data[index] = 255
                elif self._image.data[index] < 33:  # 212121
                    self._image.data[index] = 33

        elif mode == 'qgs+filter':
            self._image = self._image.color_bgr2gray()
            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            for index, value in ndenumerate(self._image.data):
                if self._image.data[index] >= 192:  # B0B0B0
                    self._image.data[index] = 255
                elif self._image.data[index] < 33:  # 212121
                    self._image.data[index] = 33

        elif mode == 'qgs+p+filter':
            grayscale = self._image.color_bgr2gray()
            grayscale = Image(cv2.bilateralFilter(grayscale.data, 3, 64, 64))
            for index, value in ndenumerate(grayscale.data):
                if grayscale.data[index] >= 192:  # B0B0B0
                    grayscale.data[index] = 255
                elif grayscale.data[index] < 33:  # 212121
                    grayscale.data[index] = 33
            grayscale = grayscale.color_gray2bgr()

            self._image = Image(cv2.bilateralFilter(self._image.data, 3, 64, 64))
            self._pronounced_colors(grayscale)

        else:
            raise ValueError(f"Invalid mode: '{self._config.mode}'.")

        if darken:
            for row in range(1, self._image.height - 1):
                for col in range(1, self._image.width - 1):
                    value = self._image.data[row, col]
                    if value != 255 and \
                            self._image.data[row - 1, col - 1] != 255 and \
                            self._image.data[row - 1, col] != 255 and \
                            self._image.data[row - 1, col + 1] != 255 and \
                            self._image.data[row, col - 1] != 255 and \
                            self._image.data[row, col + 1] != 255 and \
                            self._image.data[row + 1, col - 1] != 255 and \
                            self._image.data[row + 1, col] != 255 and \
                            self._image.data[row + 1, col + 1] != 255:
                        self._image.data[row, col] = 33

    # ------------------------------------------------------------------------------------------------------------------
    def _remove_average(self) -> Mat | ndarray[Any, dtype[integer[Any] | floating[Any]]]:
        b_total = 0
        g_total = 0
        r_total = 0
        total_pixels = 0
        width, height = self._image.size
        for i in range(width):
            for j in range(height):
                b, g, r = self._image.data[j, i]
                max_value = max(b, g, r)
                min_value = min(b, g, r)
                difference = max_value - min_value
                is_grayish = difference <= 50 or (0.299 * int(r) + 0.587 * int(g) + 0.114 * int(b)) < 64
                if not is_grayish:
                    b_total += int(b)
                    g_total += int(g)
                    r_total += int(r)
                    total_pixels += 1

        if total_pixels > 0:
            avg_b = b_total // total_pixels
            avg_g = g_total // total_pixels
            avg_r = r_total // total_pixels
        else:
            avg_b = 0
            avg_g = 0
            avg_r = 0

        temp = Image.empty_color_image(width, height, (avg_b, avg_g, avg_r))
        data = cv2.subtract(self._image.data, temp.data)
        for i in range(width):
            for j in range(height):
                b, g, r = self._image.data[j, i]
                max_value = max(b, g, r)
                min_value = min(b, g, r)
                difference = max_value - min_value
                is_grayish = difference <= 50 or (0.299 * int(r) + 0.587 * int(g) + 0.114 * int(b)) < 64
                if is_grayish:
                    data[j, i] = self._image.data[j, i]
                else:
                    b, g, r = data[j, i]
                    data[j, i] = (255 - b, 255 - g, 255 - r)
        return data

    # ------------------------------------------------------------------------------------------------------------------
    def _diaper_duty(self):
        hsv_image = self._image.color_bgr2hsv()
        width, height = self._image.size
        for i in range(width):
            for j in range(height):
                h, s, v = hsv_image.data[j, i]
                if 16 <= h <= 24 and s <= 128 and v >= 50:
                    # Color is yellowish brownish.
                    self._image.data[j, i] = Image.COLOR_BGR_WHITE

    # ------------------------------------------------------------------------------------------------------------------
    def _pronounced_colors_old(self, grayscale: Image):
        bgr_weights = [110, 125, 120]
        for row in range(self._image.height):
            for col in range(self._image.width):
                value = self._image.data[row, col]
                above_threshold = 0
                below_threshold = 0
                for i in range(3):
                    if value[i] <= bgr_weights[i]:
                        below_threshold += 1
                    else:
                        above_threshold += 1
                if above_threshold == 3 or below_threshold == 3:
                    # Not a primary color or a combination of two primary colors.
                    self._image.data[row, col] = grayscale.data[row, col]

    # ------------------------------------------------------------------------------------------------------------------
    def _pronounced_colors(self, grayscale: Image):
        hsv_image = self._image.color_bgr2hsv()
        for row in range(self._image.height):
            for col in range(self._image.width):
                h, s, v = hsv_image.data[row, col]
                is_pronounced_color = (s >= 40 and v >= 40 and not np.array_equal(grayscale.data[row, col],
                                                                                  Image.COLOR_BGR_WHITE)) or \
                                      (s >= 75 and v >= 128)

                if not is_pronounced_color:
                    self._image.data[row, col] = grayscale.data[row, col]

    # ------------------------------------------------------------------------------------------------------------------
    def _post_process_image(self):
        """
        Post-processes the image according to the post-processing mode.
        """
        if self._config.post == 'none':
            pass
        elif self._config.post == 'rcw':
            self._image = self._image.rotate90(cv2.ROTATE_90_CLOCKWISE)
        else:
            raise ValueError(f"Invalid post processing: '{self._config.post}'.")

# ----------------------------------------------------------------------------------------------------------------------
