import subprocess
from csv import reader
from pathlib import Path
from typing import List

import cv2
import img2pdf
import pikepdf
import PIL
from pikepdf import Matrix, Name, Rectangle
from pikepdf.canvas import Canvas, Color, Text
from PIL import Image as PilImage

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
        self._texts = []

        self._run_tesseract()
        self._create_pdf()
        self._save_pdf()

    # ------------------------------------------------------------------------------------------------------------------
    def _run_tesseract(self) -> None:
        """
        Runs tesseract on the image.

        """
        self._io.text('')
        self._io.title('OCR')

        self._io.text(f'Running tesseract on <fso>{self._image_path}</fso>.')

        tsv_path = self._config.tmp_path / self._image_path.stem
        command = ['tesseract',
                   '--psm',
                   self._config.ocr_psm,
                   '-l',
                   self._config.ocr_language,
                   '--dpi',
                   str(self._config.dpi),
                   str(self._image_path),
                   str(tsv_path),
                   'tsv']
        self._io.log_verbose('')
        self._io.log_verbose(f'Running: {" ".join(command)}')
        subprocess.run(command)

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
    def _save_pdf(self) -> None:
        """
        Saves the image and text found by OCR in a PDF.
        """
        self._io.text('')
        self._io.title('Saving PDF')

        PIL.Image.MAX_IMAGE_PIXELS = self._image.width * self._image.height

        if self._config.quality == 100:
            temp_filename = self._config.tmp_path / 'ocr.png'
            self._image.write(temp_filename, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        else:
            temp_filename = self._config.tmp_path / 'ocr.jpg'
            self._image.write(temp_filename, [cv2.IMWRITE_JPEG_QUALITY, self._config.quality])

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
        pdf.save(self._config.output_path)

        self._io.text(f'Saved PDF as <fso>{self._config.output_path}</fso>.')

# ----------------------------------------------------------------------------------------------------------------------
