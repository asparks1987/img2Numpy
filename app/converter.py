from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Literal
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class ConversionOptions:
    color: bool = True
    normalize: bool = False
    normalize_mode: Literal["none", "0..1", "-1..1"] | None = None
    channel_mode: Literal["RGB", "RGBA", "L"] | None = None
    dtype: str | None = None
    flatten: bool = False


def _load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    image = Image.open(BytesIO(image_bytes))
    image.load()
    return image


def image_bytes_to_array(image_bytes: bytes, options: ConversionOptions | None = None) -> np.ndarray:
    """Convert image bytes to a numpy array."""
    options = options or ConversionOptions()

    image = _load_image_from_bytes(image_bytes)
    if options.channel_mode is not None:
        image = image.convert(options.channel_mode)
    elif not options.color:
        image = image.convert("L")

    array = np.array(image)
    normalize_mode = options.normalize_mode or ("-1..1" if options.normalize else "none")
    if normalize_mode == "0..1":
        array = array.astype(np.float32) / 255.0
    elif normalize_mode == "-1..1":
        array = np.interp(array, (0, 255), (-1, 1))
    elif normalize_mode != "none":
        raise ValueError(f"Unsupported normalize mode: {normalize_mode}")

    if options.dtype:
        try:
            array = array.astype(options.dtype)
        except TypeError as exc:
            raise ValueError(f"Unsupported dtype: {options.dtype}") from exc
        except ValueError as exc:
            raise ValueError(f"Could not cast array to dtype: {options.dtype}") from exc

    if options.flatten:
        array = array.reshape(-1)

    return array


def image_file_to_array(path: str | Path, options: ConversionOptions | None = None) -> np.ndarray:
    file_path = Path(path)
    image_bytes = file_path.read_bytes()
    return image_bytes_to_array(image_bytes, options=options)
