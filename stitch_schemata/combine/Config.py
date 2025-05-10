from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """
    The configuration of StichSchemata.
    """
    output_path: Path
    """
    The path to the combined output file. 
    """
