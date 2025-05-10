import datetime
from pathlib import Path
from typing import List

import pikepdf

from stitch_schemata.combine.Config import Config
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO


class Combine:
    """
    Class for combining PDF/A-1b conformed documents into a single PDF/A-1b document.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: StitchSchemataIO, config: Config, paths: List[Path]):
        """
        Object constructor.

        :param io:The Output decorator.
        :param paths: The paths to the PDF documents.
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

    # ------------------------------------------------------------------------------------------------------------------
    def combine(self) -> None:
        """
        Combines the PDF/A-1b conformed documents into a single PDF/A-1b document.
        """
        self._io.text('')
        self._io.title('Combining PDF Documents')

        pdf_combined = pikepdf.open(Path(__file__).resolve().parent.parent / 'data/empty.pdf')
        versions = [float(pdf_combined.pdf_version)]

        for path in self._paths:
            self._io.text(f'Combining <fso>{path.name}</fso>.')

            pdf = pikepdf.open(path)
            for page in pdf.pages:
                pdf_combined.pages.append(page)

                new_page = pdf_combined.pages[-1]
                if pikepdf.Name.Annots in page:
                    pdf_temp = pikepdf.Pdf.new()
                    pdf_temp.pages.append(page)
                    indirect_annots = pdf_temp.make_indirect(pdf_temp.pages[0].Annots)
                    new_page.Annots = pdf_combined.copy_foreign(indirect_annots)

            versions.append(float(pdf.pdf_version))

        with pdf_combined.open_metadata() as meta:
            meta.mark = False
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
            meta['xmp:CreateDate'] = now
            meta['xmp:MetadataDate'] = now
            meta['xmp:CreatorTool'] = 'https://github.com/MagicSmokeBlog/stitch-schemata'

        self._io.text('')
        self._io.text(f'Saving combined PDF document as <fso>{self._config.output_path}</fso>.')
        pdf_combined.save(self._config.output_path, min_version=str(max(versions)))

# ----------------------------------------------------------------------------------------------------------------------
