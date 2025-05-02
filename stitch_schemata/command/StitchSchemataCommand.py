import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Tuple

from cleo.commands.command import Command
from cleo.helpers import argument, option

from stitch_schemata.helper.Config import Config
from stitch_schemata.helper.StitchError import StitchError
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO
from stitch_schemata.stitch.Stitch import Stitch


class StitchSchemataCommand(Command):
    """
    The stratum command: combination of constants, loader, and wrapper commands.
    """
    name = 'stitch'
    description = 'Stitches scanned circuit schema pages'
    options = [
        option(long_name='output',
               short_name='o',
               description='The stitched output file.',
               default='stitched.png',
               flag=False),
        option(long_name='margin',
               description='The margin applied when searching for tiles.',
               default=50,
               flag=False),
        option(long_name='overlap_min',
               description='The minimum overlap of scanned pages.',
               default=0.1,
               flag=False),
        option(long_name='tile-width',
               description='The width of a tile.',
               default=300,
               flag=False),
        option(long_name='tile-height',
               description='The height of a tile.',
               default=300,
               flag=False),
        option(long_name='tile-contrast-min',
               description='The minimum required contrast for find the top and bottom tiles.',
               default=10.0,
               flag=False),
        option(long_name='tile-match-min',
               description='The minimum required match for finding a tile.',
               default=0.8,
               flag=False),
        option(long_name='tile-iterations-max',
               description='The maximum number of iterations allowed for finding a tile.',
               default=5,
               flag=False),
        option(long_name='quality',
               description='The quality of the stitched image when saved as jpeg or pdf.',
               default=90,
               flag=False),
        option(long_name='tile-hint',
               description='The centers of the top and bottom tiles of a scanned image (basename:x,y;x,y).',
               flag=False,
               multiple=True)]
    arguments = [argument(name='pages', description='The scanned circuit schema pages.', optional=False, multiple=True)]

    # ------------------------------------------------------------------------------------------------------------------
    def handle(self) -> int:
        """
        Executes the stitch command.
        """
        io = StitchSchemataIO(self._io.input, self._io.output, self._io.error_output)
        tmp = tempfile.TemporaryDirectory(prefix='stitch-schemata-', dir=os.getcwd(), delete=not io.is_verbose())
        config = self._create_config(Path(tmp.name))

        stitch = Stitch(io, config)
        stitch.stitch([Path(path) for path in self.argument('pages')])

        io.text('')

        tmp.cleanup()

        return 0

    # ------------------------------------------------------------------------------------------------------------------
    def _create_config(self, tmp_path: Path) -> Config:
        """
        Creates a Config object from the given option and arguments.

        :param tmp_path: The path to the temp folder.
        """
        return Config(margin=int(self.option('margin')),
                      overlap_min=float(self.option('overlap_min')),
                      tile_width=int(self.option('tile-width')),
                      tile_height=int(self.option('tile-height')),
                      tile_contrast_min=float(self.option('tile-contrast-min')),
                      tile_match_min=float(self.option('tile-match-min')),
                      tile_iterations_max=int(self.option('tile-iterations-max')),
                      tmp_path=tmp_path.absolute(),
                      output_path=Path(self.option('output')),
                      quality=int(self.option('quality')),
                      tile_hints=self._extract_tile_hints())

    # ------------------------------------------------------------------------------------------------------------------
    def _extract_tile_hints(self) -> Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Extracts the tile hints from the given options.
        """
        title_hints = {}
        for tile_hint in self.option('tile-hint'):
            parts = re.match(r'(?P<basename>.+):(?P<top_x>\d+),(?P<top_y>\d+);(?P<bottom_x>\d+),(?P<bottom_y>\d+)',
                             tile_hint)
            if parts is None:
                raise StitchError(f'Invalid tile hint: {tile_hint}')
            title_hints[parts.group('basename')] = ((parts.group('top_x'), parts.group('top_y')),
                                                    (parts.group('bottom_x'), parts.group('bottom_y')))

        return title_hints

# ----------------------------------------------------------------------------------------------------------------------
