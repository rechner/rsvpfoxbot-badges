from PIL import Image, ImageDraw, ImageFont
from collections import namedtuple
from builtins import property
import importlib.util
import os
import sys

DEFAULT_DPI = 300.0

MODE_BW = '1' # Don't use this with truetype fonts.
MODE_GRAYSCALE = 'L'
MODE_GRAYSCALE_ALPHA = 'LA'
MODE_COLOR = 'RGB'
MODE_COLOR_ALPHA = 'RGBA'

DEFAULT_COLOR_LOOKUP = {
    MODE_BW: ((1,), (0,)),
    MODE_GRAYSCALE: ((255,), (0,)),
    MODE_GRAYSCALE_ALPHA: ((255, 0), (0, 255)),
    MODE_COLOR: ((255, 255, 255), (0, 0, 0)),
    MODE_COLOR_ALPHA: ((255, 255, 255, 0), (0, 0, 0, 255)),
}

def _inch_wrapper(func):
    def inch_wrapped(self, xy, *args, **kwargs):
        if 'width' in kwargs:
            kwargs['width'] = self.in_to_px(kwargs['width'])
        self._update_fill(kwargs)
        return func(self, self.in_to_px(xy), *args, **kwargs)
    return inch_wrapped

def _descend_into_madness(func, func_name):
    def descent(*values, dpi=DEFAULT_DPI):
        if len(values) == 0:
            return tuple()
        if len(values) == 1:
            if isinstance(values[0], (int, float)):
                return func(values[0], dpi)
            if isinstance(values[0], tuple):
                return descent(*values[0], dpi=dpi)
            if isinstance(values[0], list):
                return [descent(val, dpi=dpi) for val in values[0]]
            raise TypeError('{} must be int, float, list or tuple and not {}.'.format(func_name, type(values[0]).__name__))
        return tuple(descent(val, dpi=dpi) for val in values)
    return descent

in_to_px = _descend_into_madness(lambda n, dpi: int(n * dpi), 'in_to_px')
px_to_in = _descend_into_madness(lambda n, dpi: n / dpi, 'px_to_in')

class ImageDrawInches(ImageDraw.ImageDraw):
    def in_to_px(self, *values):
        return in_to_px(*values, dpi=self._dpi)

    def px_to_in(self, *values):
        return px_to_in(*values, dpi=self._dpi)

    def __init__(self, im, mode=None, *, dpi=DEFAULT_DPI, fill_color=None):
        super().__init__(im, mode)
        self._dpi = float(dpi)
        self._fill_color = fill_color

    arc = _inch_wrapper(ImageDraw.ImageDraw.arc)
    bitmap = _inch_wrapper(ImageDraw.ImageDraw.bitmap)
    chord = _inch_wrapper(ImageDraw.ImageDraw.chord)
    ellipse = _inch_wrapper(ImageDraw.ImageDraw.ellipse)
    line = _inch_wrapper(ImageDraw.ImageDraw.line)
    pieslice = _inch_wrapper(ImageDraw.ImageDraw.pieslice)
    point = _inch_wrapper(ImageDraw.ImageDraw.point)
    polygon = _inch_wrapper(ImageDraw.ImageDraw.polygon)
    rectangle = _inch_wrapper(ImageDraw.ImageDraw.rectangle)

    def paste(self, im, box=None):
        print(dir(self.im))
        self.im.paste(im)

    def _update_fill(self, kwargs):
        if 'fill' not in kwargs and self._fill_color is not None:
            kwargs['fill'] = self._fill_color

    @staticmethod
    def _basic_to_str(text):
        if isinstance(text, bytes):
            return text.decode('utf-8')
        if isinstance(text, (int, float)):
            return str(text)
        return text

    def text(self, xy, text, **kwargs):
        self._update_fill(kwargs)
        return super().text(self.in_to_px(xy), self._basic_to_str(text), **kwargs)

    def multiline_text(self, xy, text):
        self._update_fill(kwargs)
        return super().multiline_text(self.in_to_px(xy), self._basic_to_str(text), **kwargs)

    def textsize(self, text, **kwargs):
        return self.px_to_in(*super().textsize(self._basic_to_str(text), **kwargs))

    def multiline_textsize(self, text, **kwargs):
        return self.px_to_in(*super().multiline_textsize(self._basic_to_str(text), **kwargs))

    @property
    def dpi(self):
        return self._dpi

    def centertext(self, xy, text, *, h_align='center', v_align='center', max_width=None, **kwargs):
        self._update_fill(kwargs)
        size_args = {k: kwargs[k] for k in ('font', 'spacing', 'direction', 'features', 'language') if k in kwargs}
        text = self._basic_to_str(text)

        w, h = super().textsize(text, **size_args)
        if max_width is not None:
            max_width = self.in_to_px(max_width)
            while text and w > max_width:
                text = text[:-1]
                w, h = super().textsize(text, **size_args)

        x, y = self.in_to_px(xy)

        if h_align == 'center':
            x = int(x) - int(w / 2)
        elif h_align == 'right':
            x = int(x) - int(w)
        elif h_align == 'left':
            x = int(x)
        else:
            raise ValueError('h_align must be left, right or center and not {!r}'.format(h_align))

        if v_align == 'center':
            y = int(y) - int(h / 2)
        elif v_align == 'bottom':
            y = int(y) - int(h)
        elif v_align == 'top':
            y = int(y)
        else:
            raise ValueError('v_align must be top, bottom or center and not {!r}'.format(h_align))

        super().text((x, y), text, **kwargs)

class TemplateError(Exception):
    pass

def _use_color_defaults(image_mode, background_color, foreground_color):
    try:
        if background_color is None:
            background_color = DEFAULT_COLOR_LOOKUP[image_mode][0]
        if foreground_color is None:
            foreground_color = DEFAULT_COLOR_LOOKUP[image_mode][1]
    except KeyError:
        raise TemplateError("I don't know how to handle the image mode {!r}. You must manually specify background_color and foreground_color.".format(image_mode))
    return background_color, foreground_color

class BadgeTemplate:
    def __init__(self, size, draw_func, *, image_mode=MODE_GRAYSCALE, dpi=DEFAULT_DPI, default_font=None, background_color=None, foreground_color=None):
        self._dpi = float(DEFAULT_DPI)
        self._draw_func = draw_func
        self._size = size
        self._default_font = None
        self._image_mode = image_mode
        self._bg_color, self._fg_color = _use_color_defaults(image_mode, background_color, foreground_color)

    class Renderer:
        def __init__(self, image, draw, dpi, default_font):
            self._fonts = {}
            self._dpi = dpi
            self._default_font = default_font
            self.height = px_to_in(image.height, dpi=dpi)
            self.width = px_to_in(image.width, dpi=dpi)
            self.draw = draw
            self.image = image

        def register_font(self, alias, size_in, font_file=None):
            if font_file is None:
                if self._default_font is None:
                    raise TemplateError('You have to explicitly specify a font when there is no default configured.')
                font_file = self._default_font
            self._fonts[alias] = ImageFont.truetype(font_file, in_to_px(size_in, dpi=self._dpi))

        def font(self, alias):
            return self._fonts[alias]

    def draw_badge(self, renderer, data):
        self._draw_func(renderer, data)

    def render(self, data, fp, format=None, background=None):
        if background is None:
          image = Image.new(self._image_mode, in_to_px(self._size, dpi=self._dpi), self._bg_color)
        else:
          image = Image.open(background).convert(self._image_mode)
        draw = ImageDrawInches(image, self._image_mode, fill_color=self._fg_color)
        renderer = self.Renderer(image, draw, self._dpi, self._default_font)
        self.draw_badge(renderer, data)
        image.save(fp, format)

    @property
    def cups_media(self):
        # Yes, this is intentionally backwards. CUPS is weird.
        return 'Custom.{}x{}in'.format(self._size[1], self._size[0])

def make_template(width_in, height_in, *, image_mode=MODE_GRAYSCALE, dpi=DEFAULT_DPI, default_font=None, background_color=None, foreground_color=None):
    background_color, foreground_color = _use_color_defaults(image_mode, background_color, foreground_color)

    def subclass_init(self, *, dpi=dpi, default_font=default_font):
        self._dpi = dpi
        self._size = (width_in, height_in)
        self._default_font = default_font
        self._image_mode = image_mode
        self._bg_color = background_color
        self._fg_color = foreground_color

    def make_template_decorator(draw_badge_func):
        return type(
            draw_badge_func.__name__,
            (BadgeTemplate,),
            {
                'draw_badge': lambda self, badge, data: draw_badge_func(badge, data),
                '__init__': subclass_init
            }
        )

    return make_template_decorator


if __name__ == "__main__":
    from default_badge import DefaultBadgeTemplate
    badge = DefaultBadgeTemplate(default_font='DejaVuSans_Bold')

    #with open('rechner.jpeg', 'rb') as icon:
    if True:
      icon = None
      data = {
        'line1' : "\ud83c\udf38Tohru😺",
        'line2' : "He/Him",
        'icon' : icon,
      }

      badge.render(data, 'test.png', background='template.png')

