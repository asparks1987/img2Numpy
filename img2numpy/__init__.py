from __future__ import annotations

from .capabilities import decoder_capabilities, supported_formats
from .client import Img2NumpyClient
from .core import convert, convert_many, convert_result
from .exceptions import (
    APIClientError,
    APIResponseError,
    ConversionError,
    Img2NumpyError,
    NPZError,
    UnsupportedFormatError,
)
from .npz import load_npz, save_npz
from .options import ConversionOptions
from .results import BatchResult, ConversionResult, NPZLoadResult

__all__ = [
    "APIClientError",
    "APIResponseError",
    "BatchResult",
    "ConversionError",
    "ConversionOptions",
    "ConversionResult",
    "Img2NumpyClient",
    "Img2NumpyError",
    "NPZError",
    "NPZLoadResult",
    "UnsupportedFormatError",
    "convert",
    "convert_many",
    "convert_result",
    "decoder_capabilities",
    "load_npz",
    "save_npz",
    "supported_formats",
]
