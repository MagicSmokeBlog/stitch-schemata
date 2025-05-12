from cleo.application import Application
from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity

from stitch_schemata.command.CombineCommand import CombineCommand
from stitch_schemata.command.OcrCommand import OcrCommand
from stitch_schemata.command.StitchSchemataCommand import StitchSchemataCommand
from stitch_schemata.io.StitchSchemataIO import StitchSchemataIO


class StitchSchemataApplication(Application):
    """
    The StitchSchemata application.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self):
        """
        Object constructor
        """
        Application.__init__(self, 'stitch-schemata', '0.0.0')

        self.add(CombineCommand())
        self.add(OcrCommand())
        self.add(StitchSchemataCommand())

    # ------------------------------------------------------------------------------------------------------------------
    def render_error(self, error: Exception, io: IO) -> None:
        if io.output.verbosity == Verbosity.NORMAL:
            my_io = StitchSchemataIO(io.input, io.output, io.error_output)
            lines = [error.__class__.__name__, str(error)]
            my_io.error(lines)
        else:
            Application.render_error(self, error, io)

# ----------------------------------------------------------------------------------------------------------------------
