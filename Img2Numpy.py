"""Legacy helper module for converting images to numpy arrays.

This module is kept for backwards compatibility while the project evolves into
an API + browser application.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np

from app.converter import ConversionOptions, image_file_to_array


def load_image(image_name):
    if not os.path.isfile(image_name):
        raise FileNotFoundError(f"Image file '{image_name}' does not exist.")
    from PIL import Image

    return Image.open(image_name)


def img2numpy(image_name, color=False):
    try:
        array = image_file_to_array(image_name, options=ConversionOptions(color=color, normalize=True))
        return (image_name, array)
    except Exception as e:
        raise Exception(f"Failed to process image '{image_name}'.") from e


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
