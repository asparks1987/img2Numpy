from setuptools import setup, find_packages

setup(
    name='img2numpy',
    version='0.0.1a', 
    url='https://github.com/asparks1987/img2Numpy',
    author='Aryn M. Sparks',
    author_email='Aryn.sparks1987@gmail.com',
    description='A library for comverting images to numpy arrays.',
    packages=find_packages(),    
    install_requires=['Pillow','numpy'],
)