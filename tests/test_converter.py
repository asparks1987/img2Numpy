from io import BytesIO

import numpy as np
from PIL import Image

from app.converter import ConversionOptions, image_bytes_to_array


def make_image_bytes(mode: str = "RGB") -> bytes:
    image = Image.new(mode, (2, 2), color=(255, 0, 0) if mode == "RGB" else 100)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_bytes_to_array_color_default():
    array = image_bytes_to_array(make_image_bytes("RGB"))
    assert array.shape == (2, 2, 3)


def test_image_bytes_to_array_grayscale_normalized():
    options = ConversionOptions(color=False, normalize=True)
    array = image_bytes_to_array(make_image_bytes("RGB"), options=options)
    assert array.shape == (2, 2)
    assert array.min() >= -1
    assert array.max() <= 1


def test_image_bytes_to_array_zero_one_and_dtype():
    options = ConversionOptions(normalize_mode="0..1", dtype="float32")
    array = image_bytes_to_array(make_image_bytes("RGB"), options=options)
    assert array.dtype == np.float32
    assert array.min() >= 0
    assert array.max() <= 1


def test_image_bytes_to_array_channel_and_flatten():
    options = ConversionOptions(channel_mode="L", flatten=True)
    array = image_bytes_to_array(make_image_bytes("RGB"), options=options)
    assert array.shape == (4,)
