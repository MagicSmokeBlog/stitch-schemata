# ----------------------------------------------------------------------------------------------------------------------
def debug_seq_value() -> int:
    """
    Returns the sequence number of saved images for debugging purposes.
    """

    value = debug_seq_value.debug_seq
    debug_seq_value.debug_seq += 1

    return value


# ----------------------------------------------------------------------------------------------------------------------
debug_seq_value.debug_seq = 0
