import numpy as np


def check_color_ratio(frame, hex_color, tolerance=20, min_ratio=0.1):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    target = np.array([b, g, r])
    lower = np.clip(target - tolerance, 0, 255)
    upper = np.clip(target + tolerance, 0, 255)
    mask = np.all((frame >= lower) & (frame <= upper), axis=2)
    ratio = mask.sum() / mask.size
    return ratio >= min_ratio, ratio
