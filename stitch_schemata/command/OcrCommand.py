import tempfile
from pathlib import Path

from cleo.commands.command import Command
from cleo.helpers import option

from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.ocr.Config import Config
from stitch_schemata.ocr.Ocr import Ocr


class OcrCommand(Command):
    """
    The OCR command.
    """
    name = 'ocr'
    description = 'Generates a PDF file with OCR from an image.'
    options = [option(long_name='input',
                      short_name='i',
                      description='The path to the input image.',
                      flag=False,
                      value_required=True),
               option(long_name='output',
                      short_name='o',
                      description='The path ot the output PDF with OCR.',
                      flag=False,
                      value_required=True),
               option(long_name='quality',
                      description='The quality of the image when saved in the PDF.',
                      default=90,
                      flag=False),
               option(long_name='dpi',
                      description='The resolution of the scanned images in DPI.',
                      default=600,
                      flag=False),
               option(long_name='ocr-psm',
                      description='The page segmentation mode used for OCR.',
                      default='sparse_text',
                      flag=False),
               option(long_name='ocr-language',
                      description='The language(s) used for OCR.',
                      default='deu+eng+fra+nld',
                      flag=False),
               option(long_name='ocr-confidence-min',
                      description='The minimum confidence level of OCR for a piece of recognized text to be included in the OCR layer.',
                      default='60.0',
                      flag=False)]

    # ------------------------------------------------------------------------------------------------------------------
    def handle(self) -> int:
        """
        Executes the OCR command.
        """
        io = StitchSchemataIO(self._io.input, self._io.output, self._io.error_output)
        tmp = tempfile.TemporaryDirectory(prefix='stitch-schemata-', dir=Path.cwd(), delete=not io.is_debug())
        config = self._create_config(Path(tmp.name))

        ocr = Ocr(io, config)
        ocr.ocr()

        io.text('')

        return 0

    # ------------------------------------------------------------------------------------------------------------------
    def _create_config(self, tmp_path: Path) -> Config:
        """
        Creates a Config object from the given option and arguments.

        :param tmp_path: The path to the temp folder.
        """
        tmp_path = tmp_path.resolve()
        cwd = Path.cwd().resolve()
        if tmp_path.is_relative_to(cwd.resolve()):
            tmp_path = tmp_path.relative_to(cwd)

        return Config(dpi=int(self.option('dpi')),
                      tmp_path=tmp_path,
                      input_path=Path(self.option('input')),
                      output_path=Path(self.option('output')),
                      quality=int(self.option('quality')),
                      ocr_psm=self.option('ocr-psm'),
                      ocr_language=self.option('ocr-language'),
                      ocr_confidence_min=float(self.option('ocr-confidence-min')))

# ----------------------------------------------------------------------------------------------------------------------
