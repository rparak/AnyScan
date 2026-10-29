"""
Measure a colour pair the way the theme does.

    python contrast.py '#640ABA' '#FFFFFF' [more pairs ...]

For each pair: the WCAG contrast ratio (4.5:1 text, 3:1 graphic), CIE76 dE (12 is the distinctness floor) and both
colours' LCh. Use it before adding a token, and quote the numbers in the token's comment.
"""
import math
import sys


def Linear(c: float) -> float:
    c /= 255.0
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def Rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def Luminance(h: str) -> float:
    r, g, b = (Linear(c) for c in Rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def Lab(h: str):
    r, g, b = (Linear(c) for c in Rgb(h))
    x, y, z = ((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b,
               (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def main() -> int:
    colours = sys.argv[1:]
    if len(colours) < 2 or len(colours) % 2:
        print(__doc__)
        return 2
    for a, b in zip(colours[0::2], colours[1::2]):
        la, lb = Luminance(a), Luminance(b)
        ratio = (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
        lab_a, lab_b = Lab(a), Lab(b)
        lch = lambda l: '(L* %.1f, C* %.1f, h %.0f)' % (l[0], math.hypot(l[1], l[2]), math.degrees(math.atan2(l[2], l[1])) % 360)
        print('%s on %s: %.2f:1, dE76 %.1f; %s %s, %s %s' % (a, b, ratio, math.dist(lab_a, lab_b), a, lch(lab_a), b,
                                                            lch(lab_b)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
