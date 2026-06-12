from __future__ import annotations


class Img2NumpyError(Exception):
    """Base error for the img2numpy SDK."""


class ConversionError(Img2NumpyError):
    """Raised when a source cannot be converted to a NumPy array."""


class UnsupportedFormatError(ConversionError):
    """Raised when a format requires an unavailable optional decoder."""


class NPZError(Img2NumpyError):
    """Raised when NPZ serialization or loading fails."""


class APIClientError(Img2NumpyError):
    """Raised when a remote img2numpy API request fails."""


class APIResponseError(APIClientError):
    """Raised when the remote API returns an error response."""

