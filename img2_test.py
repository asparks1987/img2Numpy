import Img2Numpy
import os

Img2Numpy.folder2numpy("cats")
loaded_imgs = Img2Numpy.npz2array("cats_processed_images.npz")
image_list, image_names = Img2Numpy.tuple2lists(loaded_imgs)
print(image_list)

def print_filenames(file_paths):
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        filename = Img2Numpy.scrub_filename(filename)
        print(filename)
        
print_filenames(image_names)