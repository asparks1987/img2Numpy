from PIL import Image
import numpy as np
import os
import re

def load_image(image_name):
    """Loads an image into a PIL Image object.

    Args:
        image_name (str): Path to the image.

    Returns:
        PIL Image object if successful, None otherwise.

    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    if not os.path.isfile(image_name):
        raise FileNotFoundError(f"Image file '{image_name}' does not exist.")
    
    return Image.open(image_name)

def img2numpy(image_name, color=False):
    """Converts an image file to a normalized numpy array.

    Args:
        image_name (str): Path to the image.
        color (bool): If True, keeps the color information. Otherwise, converts the image to grayscale.

    Returns:
        tuple: The image name and the normalized numpy array.

    Raises:
        Exception: If the image cannot be processed.
    """
    try:
        image = load_image(image_name)
        
        if not color:
            image = image.convert('L')

        image_array = np.array(image)
        normalized_image = np.interp(image_array, (0, 255), (-1, 1))

        return (image_name, normalized_image)
    except Exception as e:
        raise Exception(f"Failed to process image '{image_name}'.") from e

def folder2numpy(folder_path, color=False):
    """Converts all images in a folder to normalized numpy arrays.

    Args:
        folder_path (str): Path to the folder.
        color (bool): If True, keeps the color information. Otherwise, converts the images to grayscale.

    Returns:
        numpy.ndarray: The images' names and the normalized numpy arrays.

    Raises:
        FileNotFoundError: If the folder does not exist.
        Exception: If the images cannot be processed.
    """
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")
    
    image_data = []

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        
        try:
            image = load_image(file_path)
        except FileNotFoundError:
            continue

        img_tuple = img2numpy(file_path, color=color)
        if img_tuple is not None:
            image_data.append(img_tuple)
    
    image_data_array = np.array(image_data, dtype=object)
    np.savez_compressed(f"{folder_path}_processed_images.npz", image_data_array)

    return image_data_array

def npz2array(npz_file_path):
    """Loads a numpy array from a .npz file.

    Args:
        npz_file_path (str): Path to the .npz file.

    Returns:
        numpy.ndarray: The loaded numpy array.

    Raises:
        FileNotFoundError: If the .npz file does not exist.
    """
    if not os.path.isfile(npz_file_path):
        raise FileNotFoundError(f".npz file '{npz_file_path}' does not exist.")

    npz_data = np.load(npz_file_path, allow_pickle=True)

    return npz_data['arr_0']

def tuple2lists(input_array):
    """Converts a numpy array of tuples into two lists.

    Args:
        input_array (numpy.ndarray): A numpy array of tuples.

    Returns:
        tuple: Two lists, one for the first elements of the tuples and one for the second elements.

    Raises:
        TypeError: If the input is not a numpy array.
    """
    if not isinstance(input_array, np.ndarray):
        raise TypeError("The input must be a numpy array.")

    images = []
    names = []

    for img_tuple in input_array:
        names.append(img_tuple[0])
        images.append(img_tuple[1])

    return images, names

def scrub_filename(filename):
    """Removes the file extension and numbers from a filename.

    Args:
        filename (str): The filename.

    Returns:
        str: The scrubbed filename.
    """
    filename_without_extension = os.path.splitext(filename)[0]
    cleaned_filename = re.sub(r'\d+', '', filename_without_extension)

    return cleaned_filename
