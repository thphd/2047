from functools import *
from PIL import Image, ImageDraw, ImageChops
import Identicon
BACKGROUND_COLOR = (244,)*3
Identicon._crop_coner_round = lambda a,b:a # don't cut corners, please
def _set_pixels(flatten_grid):
    # len(list) should be a squared of integer value
    # Caculate pixels
    pixels = []
    unit = 100/7
    for i, val in enumerate(flatten_grid):
        x = i%5 * unit + unit
        y = i//5 * unit + unit

        top_left = (round(x), round(y))
        bottom_right = (round(x + unit), round(y + unit))

        pixels.append([top_left, bottom_right])

    return pixels
Identicon._set_pixels = _set_pixels

identicon_bkgnd = Image.open('./templates/images/avatar-max-img-hc.png').convert('RGB')
white = Image.new('RGB', (100,100), BACKGROUND_COLOR)

def _draw_identicon(color, grid_list, pixels):
    identicon_im = white.copy()
    # identicon_im = identicon_bkgnd.copy()
    draw = ImageDraw.Draw(identicon_im)
    for grid, pixel in zip(grid_list, pixels):
        if grid != 0: # for not zero
            draw.rectangle(pixel, fill=color)

    identicon_im = ImageChops.blend(identicon_im, white, 0.7)
    out = ImageChops.multiply(identicon_im, identicon_bkgnd)
    return out
Identicon._draw_identicon = _draw_identicon

@lru_cache(maxsize=4096)
def render_identicon(string):
    identicon = Identicon.render(string)
    return identicon
