from pathlib import Path

from cleo.commands.command import Command
from cleo.helpers import argument, option

from stitch_schemata.combine.Combine import Combine
from stitch_schemata.combine.Config import Config
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO


class CombineCommand(Command):
    """
    The combine command.
    """
    name = 'combine'
    description = 'Combines PDF/A-1b conformed documents into a single PDF/A-1b document.'
    options = [option(long_name='output',
                      short_name='o',
                      description='The combined output file.',
                      flag=False,
                      value_required=True), ]
    arguments = [argument(name='pages', description='The PDF documents.', optional=False, multiple=True)]

    # ------------------------------------------------------------------------------------------------------------------
    def handle(self) -> int:
        """
        Executes the stitch command.
        """
        io = StitchSchemataIO(self._io.input, self._io.output, self._io.error_output)
        config = self._create_config()

        combine = Combine(io, config, [Path(path) for path in self.argument('pages')])
        combine.combine()

        io.text('')

        return 0

    # ------------------------------------------------------------------------------------------------------------------
    def _create_config(self) -> Config:
        """
        Creates a Config object from the given option and arguments.
        """
        return Config(output_path=Path(self.option('output')))

# ----------------------------------------------------------------------------------------------------------------------
