#!/usr/bin/env python3
"""Crop + upscale a region of a rasterised schematic page for close reading.

The primary schematic (circuit drawing) is PAGE 4 of "Primary BOM and schematic.pdf" and is dense;
rasterise it high-DPI first, then crop fractional regions (see circuit.md "Crop index").

Usage:
    # 1. Rasterise the schematic page once (needs poppler's pdftoppm):
    pdftoppm -f 4 -l 4 -r 300 -png "Primary BOM and schematic.pdf" primary_p4
    #    -> primary_p4-4.png   (backup: -f 1 -l 1 on the backup PDF)

    # 2. Crop a fractional region (x0 y0 x1 y1 are fractions 0..1 of the full page) and upscale:
    python3 crop.py primary_p4-4.png clip 0.518 0.30 0.585 0.45 6.0
    #    -> clip.png

Coordinates in circuit.md's crop index are fractions of the full rasterised page.
"""
import sys
from PIL import Image

if len(sys.argv) != 8:
    print(__doc__)
    sys.exit(1)

src, name = sys.argv[1], sys.argv[2]
x0, y0, x1, y1, sc = map(float, sys.argv[3:8])
im = Image.open(src)
W, H = im.size
c = im.crop((int(W * x0), int(H * y0), int(W * x1), int(H * y1)))
c = c.resize((int(c.width * sc), int(c.height * sc)), Image.LANCZOS)
c.save(name + ".png")
print(name + ".png", c.size)
