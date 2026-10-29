"""
Render the pixel icon set as a contact sheet, to judge a new icon beside its family.

    python icon_sheet.py <project_dir> out.png [--cells 1 2 5]

Imports JIC_SF_UI.Pixel_Motif from <project_dir> (so a new icon added there is drawn) and draws every icon, still
('#' cells only), in the purple on white at each cell size: 1 px (a pill), 2 px (a card head), 5 px (the busy
overlay), one row per size, labelled. Needs PyQt5 (offscreen).
"""
import argparse
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('out')
    parser.add_argument('--cells', nargs='+', type=int, default=[1, 2, 5])
    args = parser.parse_args()
    sys.path.insert(0, os.path.abspath(args.project))
    from PyQt5.QtCore import Qt, QRect
    from PyQt5.QtGui import QImage, QPainter, QFont
    from PyQt5.QtWidgets import QApplication
    from JIC_SF_UI import Style
    from JIC_SF_UI.Pixel_Motif import CONST_PIXEL_ICONS, CONST_ICON_GRID, Icon_Cells

    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    names = sorted(CONST_PIXEL_ICONS)
    slot, label_h, pad = max(args.cells) * CONST_ICON_GRID + 24, 18, 16
    width = pad * 2 + slot * len(names)
    height = pad + sum(c * CONST_ICON_GRID + label_h + pad for c in args.cells) + label_h
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(Style.Token_Color(Style.CONST_BG))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setFont(Style.Font(9))
    y = pad
    for cell in args.cells:
        p.setPen(Style.Token_Color(Style.CONST_INK_MUTE))
        p.drawText(QRect(pad, y, width, label_h), Qt.AlignLeft | Qt.AlignVCenter, '%d px cells' % cell)
        y += label_h
        for index, name in enumerate(names):
            x = pad + index * slot
            for column, row in Icon_Cells(name):
                p.fillRect(x + column * cell, y + row * cell, cell, cell, Style.Token_Color(Style.CONST_INK))
            if cell == max(args.cells):
                p.setPen(Style.Token_Color(Style.CONST_DETECTION_INK))
                p.drawText(QRect(x - 8, y + cell * CONST_ICON_GRID + 2, slot, label_h), Qt.AlignLeft, name)
        y += cell * CONST_ICON_GRID + pad + (label_h if cell == max(args.cells) else 0)
    p.end()
    image.save(args.out)
    print(args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
