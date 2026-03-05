"""Legacy smoke script for Img2Numpy module.

Prefer pytest tests under tests/ for automated checks.
"""

import Img2Numpy

print("Available helpers:", [
    Img2Numpy.img2numpy.__name__,
    Img2Numpy.folder2numpy.__name__,
    Img2Numpy.npz2array.__name__,
    Img2Numpy.tuple2lists.__name__,
    Img2Numpy.scrub_filename.__name__,
])
