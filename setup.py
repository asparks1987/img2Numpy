from setuptools import find_packages, setup

setup(
    name="img2numpy",
    version="0.1.0",
    url="https://github.com/asparks1987/img2Numpy",
    author="Aryn M. Sparks",
    description="Python SDK for converting images to NumPy arrays.",
    packages=find_packages(include=["app", "app.*", "img2numpy", "img2numpy.*"]),
    package_data={"img2numpy": ["py.typed"]},
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "jinja2",
        "python-multipart",
        "numpy",
        "Pillow",
        "httpx",
    ],
    extras_require={
        "heif": ["pillow-heif>=0.17.0"],
        "avif": ["pillow-heif>=0.17.0"],
        "svg": ["cairosvg>=2.7.1"],
        "pdf": ["pymupdf>=1.24.0"],
        "raw": ["rawpy>=0.19.0"],
        "all": [
            "pillow-heif>=0.17.0",
            "cairosvg>=2.7.1",
            "pymupdf>=1.24.0",
            "rawpy>=0.19.0",
        ],
    },
)
