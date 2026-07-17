"""Small Pillow compatibility helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PIL import Image


def pixel_data(image: Image.Image) -> Iterable[Any]:
    """Use Pillow's non-deprecated iterator while retaining Pillow 10 support."""

    flattened = getattr(image, "get_flattened_data", None)
    if callable(flattened):
        return flattened()
    return image.getdata()
