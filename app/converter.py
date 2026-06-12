from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from img2numpy import ConversionOptions as SDKConversionOptions
from img2numpy import convert as sdk_convert


@dataclass(slots=True)
class ConversionOptions:
    color: bool = True
    normalize: bool = False
    normalize_mode: Literal["none", "0..1", "-1..1"] | None = None
    channel_mode: Literal["RGB", "RGBA", "L", "LA", "CMYK", "P"] | None = None
    dtype: str | None = None
    flatten: bool = False
    frame: int | Literal["all"] | None = None
    resize: tuple[int, int] | None = None
    preserve_metadata: bool = False
    url_timeout_seconds: float = 15.0

    def to_sdk(self) -> SDKConversionOptions:
        channel_mode = self.channel_mode
        if channel_mode is None and not self.color:
            channel_mode = "L"
        normalize_mode = self.normalize_mode
        if normalize_mode is None:
            normalize_mode = "-1..1" if self.normalize else "none"
        return SDKConversionOptions(
            channel_mode=channel_mode,
            normalize_mode=normalize_mode,
            dtype=self.dtype,
            flatten=self.flatten,
            frame=self.frame,
            resize=self.resize,
            preserve_metadata=self.preserve_metadata,
            url_timeout_seconds=self.url_timeout_seconds,
        )


def load_image(image_name):
    if not os.path.isfile(image_name):
        raise FileNotFoundError(f"Image file '{image_name}' does not exist.")
    return Image.open(image_name)


def img2numpy(image_name, color=False):
    try:
        array = sdk_convert(image_name, options=ConversionOptions(color=color, normalize=True).to_sdk())
        return (image_name, array)
    except Exception as e:
        raise Exception(f"Failed to process image '{image_name}'.") from e


def image_bytes_to_array(image_bytes: bytes, options: ConversionOptions | None = None) -> np.ndarray:
    return sdk_convert(image_bytes, options=(options or ConversionOptions()).to_sdk())


def image_file_to_array(path: str | Path, options: ConversionOptions | None = None) -> np.ndarray:
    return sdk_convert(path, options=(options or ConversionOptions()).to_sdk())


def folder2numpy(folder_path, color=False):
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")

    image_data = []
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if not os.path.isfile(file_path):
            continue
        try:
            img_tuple = img2numpy(file_path, color=color)
            image_data.append(img_tuple)
        except Exception:
            continue

    image_data_array = np.array(image_data, dtype=object)
    np.savez_compressed(f"{folder_path}_processed_images.npz", image_data_array)
    return image_data_array


def npz2array(npz_file_path):
    if not os.path.isfile(npz_file_path):
        raise FileNotFoundError(f".npz file '{npz_file_path}' does not exist.")
    npz_data = np.load(npz_file_path, allow_pickle=True)
    return npz_data["arr_0"]


def tuple2lists(input_array):
    if not isinstance(input_array, np.ndarray):
        raise TypeError("The input must be a numpy array.")

    images = []
    names = []
    for img_tuple in input_array:
        names.append(img_tuple[0])
        images.append(img_tuple[1])

    return images, names


def scrub_filename(filename):
    filename_without_extension = Path(filename).stem
    cleaned_filename = re.sub(r"\d+", "", filename_without_extension)
    return cleaned_filename
