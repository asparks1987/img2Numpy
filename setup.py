from setuptools import find_packages, setup

setup(
    name="img2numpy",
    version="0.1.0",
    url="https://github.com/asparks1987/img2Numpy",
    author="Aryn M. Sparks",
    description="Browser/API app for converting images to numpy arrays.",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "jinja2",
        "python-multipart",
        "numpy",
        "Pillow",
    ],
)
