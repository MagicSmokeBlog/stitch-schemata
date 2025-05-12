from dataclasses import dataclass


@dataclass(frozen=True)
class OcrText:
    """
    Text found by Tesseract. See https://blog.tomrochette.com/tesseract-tsv-format.
    """
    level: int
    """
    Hierarchical layout (a word is in a line, which is in a paragraph, which is in a block, which is in a page), a 
    value from 1 to 5:
    1: page
    2: block
    3: paragraph
    4: line
    5: word
    """

    page_num: int
    """
    When provided with a list of images, indicates the number of the file, when provided with a multi-pages document,
    indicates the page number, starting from 1.
    """

    block_num: int
    """
    Block number within the page, starting from 0.
    """

    par_num: int
    """
    Paragraph number within the block, starting from 0.
    """

    line_num: int
    """
    Line number within the paragraph, starting from 0.
    """

    word_num: int
    """
    Word number within the line, starting from 0.
    """

    left: int
    """
    X coordinate in pixels of the text bounding box top left corner, starting from the left of the image.
    """

    top: int
    """
    Y coordinate in pixels of the text bounding box top left corner, starting from the top of the image.
    """

    width: int
    """
    Width of the text bounding box in pixels.
    """

    height: int
    """
    Height of the text bounding box in pixels.
    """

    conf: float
    """
    Confidence value, from 0 (no confidence) to 100 (maximum confidence), -1 for all level except 5.
    """

    text: str
    """
    Detected text, empty for all levels except 5.
    """
