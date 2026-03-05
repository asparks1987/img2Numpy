from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class ConversionOptions:
    color: bool = True
    normalize: bool = False


def _load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    image = Image.open(BytesIO(image_bytes))
    image.load()
    return image


def image_bytes_to_array(image_bytes: bytes, options: ConversionOptions | None = None) -> np.ndarray:
    """Convert image bytes to a numpy array."""
    options = options or ConversionOptions()

    image = _load_image_from_bytes(image_bytes)
    if not options.color:
        image = image.convert("L")

    array = np.array(image)
    if options.normalize:
        array = np.interp(array, (0, 255), (-1, 1))

    return array


def image_file_to_array(path: str | Path, options: ConversionOptions | None = None) -> np.ndarray:
    file_path = Path(path)
    image_bytes = file_path.read_bytes()
    return image_bytes_to_array(image_bytes, options=options)
