from stitch_schemata.application.StitchSchemataApplication import StitchSchemataApplication


def main() -> int:
    application = StitchSchemataApplication()
    ret = application.run()

    return ret
