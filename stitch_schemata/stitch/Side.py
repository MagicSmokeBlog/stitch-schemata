from enum import auto, Enum, STRICT


class Side(Enum, boundary=STRICT):
    """
    Enumeration for left and right side.
    """
    # ------------------------------------------------------------------------------------------------------------------
    LEFT = auto()
    """
    Left size.
    """

    RIGHT = auto()
    """
    Right size.
    """

# ----------------------------------------------------------------------------------------------------------------------
