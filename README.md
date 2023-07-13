# img2NumpyImage Processing with Numpy and PIL
This Python script allows you to process images using the Pillow library and Numpy. Images are converted to Numpy arrays for further processing and can be normalized and stored in a .npz file for efficient storage and retrieval.

Function Overview
load_image(image_name: str) -> PIL.Image
Loads an image into a PIL Image object.

Args:

image_name: Path to the image.
Returns:

PIL Image object if successful, raises FileNotFoundError otherwise.
img2numpy(image_name: str, color: bool=False) -> tuple
Converts an image file to a normalized numpy array.

Args:

image_name: Path to the image.
color: If True, keeps the color information. Otherwise, converts the image to grayscale.
Returns:

tuple: The image name and the normalized numpy array.
folder2numpy(folder_path: str, color: bool=False) -> numpy.ndarray
Converts all images in a folder to normalized numpy arrays.

Args:

folder_path: Path to the folder.
color: If True, keeps the color information. Otherwise, converts the images to grayscale.
Returns:

numpy.ndarray: The images' names and the normalized numpy arrays.
npz2array(npz_file_path: str) -> numpy.ndarray
Loads a numpy array from a .npz file.

Args:

npz_file_path: Path to the .npz file.
Returns:

numpy.ndarray: The loaded numpy array.
tuple2lists(input_array: numpy.ndarray) -> tuple
Converts a numpy array of tuples into two lists.

Args:

input_array: A numpy array of tuples.
Returns:

tuple: Two lists, one for the first elements of the tuples and one for the second elements.
scrub_filename(filename: str) -> str
Removes the file extension and numbers from a filename.

Args:

filename: The filename.
Returns:

str: The scrubbed filename.
Usage
You can import the script and use its functions as needed in your data processing pipeline. For example:
from myscript import folder2numpy, npz2array

# Convert all images in a folder to numpy arrays and save the result
folder2numpy("/path/to/my/images")

# Load the data from the saved .npz file
data = npz2array("/path/to/my/images_processed_images.npz")
This script helps in creating a seamless pipeline for image processing tasks by handling image loading, conversion, normalization, and storage. It's also designed to provide clear error messages for common issues, such as missing files or incorrect data types.

Dependencies
Numpy
Pillow
Disclaimer
Always make sure that you have the necessary permissions to read and write in the directories you use with this script.