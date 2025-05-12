from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """
    The configuration for OCR.
    """
    dpi: int
    """
    The resolution of the scanned images in DPI (Dots Per Inch). 
    """

    tmp_path: Path
    """
    The path to the temp folder. 
    """

    input_path: Path | None
    """
    The path to the image. 
    """

    output_path: Path | None
    """
    The path to the PDF with OCR. 
    """

    quality: int
    """
    The quality of the stitched image when saved as jpeg or pdf. 
    """

    ocr_psm: str
    """
    The page segmentation mode used for OCR.    
    """

    ocr_language: str
    """
    The language(s) used for OCR.
    """

    ocr_confidence_min: float
    """
    The minimum confidence level of OCR for a piece of recognized text to be included in the OCR layer.
    """
