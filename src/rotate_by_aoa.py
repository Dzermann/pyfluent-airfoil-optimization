# -*- coding: utf-8 -*-
"""
    Rotates the contour and mesh pictures of every run by its angle of attack,
    so the free stream is horizontal and the airfoil is shown pitched at its aoa.

    The aoa is read from the run's *_inputs.txt. Rotated copies are saved in a
    'rotated' subfolder next to each picture; the original pictures are untouched.

    Usage: python src/rotate_by_aoa.py <folder>   (searches the folder recursively)
"""

import re
import sys
from pathlib import Path

from PIL import Image

PICTURE = re.compile(r"(pres_cont|mach_cont|mesh)", re.IGNORECASE)  # plots (y+, residuals...) are left alone


def find_aoa(folder):
    """Return the aoa from the closest *_inputs.txt in this folder or its parents, or None."""
    for parent in [folder, *folder.parents]:
        for inputs in parent.glob("*_inputs.txt"):
            match = re.search(r"^aoa\s*=\s*(-?[\d.]+)", inputs.read_text(errors="ignore"), re.MULTILINE)
            if match:
                return float(match.group(1))
    return None


def rotate_pictures(root):
    count = 0
    for picture in sorted(Path(root).rglob("*.png")):
        if picture.parent.name == "rotated" or not PICTURE.search(picture.name + picture.parent.name):
            continue
        aoa = find_aoa(picture.parent)
        if aoa is None:
            print(f"SKIP (no aoa found): {picture}")
            continue

        out_folder = picture.parent / "rotated"
        out_folder.mkdir(exist_ok=True)

        # the flow comes in at aoa, so rotating by -aoa makes it horizontal
        with Image.open(picture) as image:
            rotated = image.convert("RGB").rotate(-aoa, resample=Image.BICUBIC, expand=True, fillcolor="white")
        rotated.save(out_folder / picture.name)
        count += 1

    print(f"PASS: {count} pictures rotated")


if __name__ == "__main__":
    rotate_pictures(sys.argv[1] if len(sys.argv) > 1 else ".")
