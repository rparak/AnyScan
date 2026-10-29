"""
Draw the JIC Smart Factory image marks on a synthetic frame and save it, to see the annotation rules at once:

    python annotate_demo.py out.png        (needs opencv-python-headless and numpy)

An OK part (purple box, chip 1, two holes found), a NOK part (dashed outer box and chip in the orange-red, its rotated
outline purple because its size is within tolerance, a missing hole dashed, a stain tinted, feature chips 2.1-2.3 on
the corners nearest its chip), a Warning (amber outline, outer box and chip, no feature marks) and the label mask.
"""
import os
import sys

import cv2
import numpy as np

from JIC_SF_UI import Theme
from JIC_SF_UI.Annotate import Draw_Object, Draw_Feature, Tint_Regions, Fill_Mask


def Rotated(cx, cy, w, h, degrees):
    a = np.radians(degrees)
    u, v = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    c = np.array([cx, cy])
    return np.float64([c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2, c + u * w / 2 + v * h / 2,
                       c - u * w / 2 + v * h / 2])


def Bbox(corners):
    x0, y0 = np.floor(corners.min(axis=0)).astype(int)
    x1, y1 = np.ceil(corners.max(axis=0)).astype(int)
    return int(x0), int(y0), int(x1 - x0), int(y1 - y0)


def main(out: str) -> None:
    frame = np.zeros((1200, 1920, 3), np.uint8)
    frame[:] = (81, 102, 26)                                  # a demo surface (BGR), not a theme colour
    ok_box, nok_box, warn_box = Theme.Verdict_Color('OK')[0], Theme.Verdict_Color('NOK')[0], \
        Theme.Verdict_Color('Warning')[0]
    parts = [Rotated(520, 600, 520, 300, 8), Rotated(1180, 560, 520, 300, -12), Rotated(1690, 980, 300, 200, 20)]
    for corners in parts:
        cv2.fillPoly(frame, [np.int32(corners)], (167, 159, 164))
    mask = np.zeros_like(frame)

    # 1: OK, two holes found.
    placed = []
    Draw_Object(frame, Bbox(parts[0]), 1, ok_box, cv2, rotated=list(map(tuple, parts[0])))
    for k, (dx, dy) in enumerate(((-150, 0), (150, 0)), 1):
        hole = Rotated(520 + dx, 600 + dy + dx * 0.14, 60, 60, 8)
        Draw_Feature(frame, hole, ok_box, True, '1.%d' % k, Bbox(parts[0]), placed, cv2, np)
    # 2: NOK for a stain and a missing hole; its outline (size) within tolerance, so purple.
    placed = []
    Draw_Object(frame, Bbox(parts[1]), 2, nok_box, cv2, rotated=list(map(tuple, parts[1])), outline_color=ok_box)
    stain = Rotated(1260, 520, 90, 50, -12)
    Tint_Regions(frame, [stain], nok_box, cv2, np)
    Draw_Feature(frame, stain, nok_box, True, '2.1', Bbox(parts[1]), placed, cv2, np)
    Draw_Feature(frame, Rotated(1030, 600, 60, 60, -12), ok_box, True, '2.2', Bbox(parts[1]), placed, cv2, np)
    Draw_Feature(frame, Rotated(1330, 620, 60, 60, -12), nok_box, False, '2.3', Bbox(parts[1]), placed, cv2, np)
    # 3: a Warning (outside the area): outline, outer box and chip in the amber, no feature marks.
    Draw_Object(frame, Bbox(parts[2]), 3, warn_box, cv2, rotated=list(map(tuple, parts[2])))

    for state, corners in zip(('OK', 'NOK', 'Warning'), parts):
        region = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillPoly(region, [np.int32(corners)], 1)
        Fill_Mask(mask, region, state)
        Draw_Object(mask, Bbox(corners), ('OK', 'NOK', 'Warning').index(state) + 1, Theme.Verdict_Color(state)[0], cv2)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if not cv2.imwrite(out, np.vstack([frame, mask])):
        sys.exit('could not write %s' % out)
    print(out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'annotate_demo.png')
