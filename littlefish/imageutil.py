"""
Image processing utility functions
"""

import logging
import io

import PIL.Image
import PIL.ImageEnhance

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


def resize_image_to_fit(image, dest_w, dest_h):
    """
    Resize the image to fit inside dest rectangle.  Resultant image may be smaller than target
    :param image: PIL.Image
    :param dest_w: Target width
    :param dest_h: Target height
    :return: Scaled image
    """
    dest_w = float(dest_w)
    dest_h = float(dest_h)
    dest_ratio = dest_w / dest_h

    # Calculate the apect ratio of the image
    src_w = float(image.size[0])
    src_h = float(image.size[1])
    src_ratio = src_w / src_h

    if src_ratio < dest_ratio:
        # Image is tall and thin - we need to scale to the right height and then pad
        scale = dest_h / src_h
        scaled_h = dest_h
        scaled_w = src_w * scale

    else:
        # Image is short and wide - we need to scale to the right height and then crop
        scale = dest_w / src_w
        scaled_w = dest_w
        scaled_h = src_h * scale

    scaled_image = image.resize((int(scaled_w), int(scaled_h)), PIL.Image.ANTIALIAS)

    return scaled_image


def resize_crop_image(image, dest_w, dest_h, pad_when_tall=False, dest_top=None, dest_left=None):
    """
    :param image: PIL.Image
    :param dest_w: Target width
    :param dest_h: Target height
    :param dest_top: Optional vertical offset when cropping (will be centred if omitted)
    :param dest_left: Optional horizontal offset when cropping (will be centred if omitted)
    :return: Scaled and cropped image
    """

    # Now we need to resize it
    dest_w = float(dest_w)
    dest_h = float(dest_h)
    dest_ratio = dest_w / dest_h

    # Calculate the apect ratio of the image
    src_w = float(image.size[0])
    src_h = float(image.size[1])
    src_ratio = src_w / src_h

    if src_ratio < dest_ratio:
        # Image is tall and thin - we need to scale to the right width and then crop
        scale = dest_w / src_w
        scaled_w = dest_w
        scaled_h = src_h * scale

        # Cropping values
        left = 0
        right = dest_w

        if dest_top is None:
            top = (scaled_h - dest_h) / 2.0
        elif dest_top < 0:
            top = 0
        elif dest_top > scaled_h - dest_h:
            top = scaled_h - dest_h
        else:
            top = dest_top

        bottom = top + dest_h
    else:
        # Image is short and wide - we need to scale to the right height and then crop
        scale = dest_h / src_h
        scaled_h = dest_h
        scaled_w = src_w * scale

        # Cropping values
        if dest_left is None:
            left = (scaled_w - dest_w) / 2.0
        elif dest_left < 0:
            left = 0
        elif dest_left > scaled_w - dest_w:
            left = scaled_w - dest_w
        else:
            left = dest_left

        right = left + dest_w
        top = 0
        bottom = dest_h

    if pad_when_tall:
        # Now, for images that are really tall and thin, we start to have issues as we only show a small section of them
        # (i.e. nasonex).  To deal with this we will resize and pad in this situation
        if (bottom - top) < (scaled_h * 0.66):
            log.info('Image would crop too much - returning padded image instead')
            return resize_pad_image(image, dest_w, dest_h)

    if src_w > dest_w or src_h > dest_h:
        # This means we are shrinking the image which is ok!
        scaled_image = image.resize((int(scaled_w), int(scaled_h)), PIL.Image.ANTIALIAS)
        cropped_image = scaled_image.crop((int(left), int(top), int(right), int(bottom)))

        return cropped_image

    elif scaled_w < src_w or scaled_h < src_h:
        # Just crop is as we don't want to stretch the image
        cropped_image = image.crop((int(left), int(top), int(right), int(bottom)))

        return cropped_image

    else:
        return image


def resize_pad_image(image, dest_w, dest_h, pad_with_transparent=False, pad_colour=None):
    """
    Resize the image and pad to the correct aspect ratio.
    :param image: PIL.Image
    :param dest_w: Target width
    :param dest_h: Target height
    :param pad_with_transparent: If True, make additional padding transparent
    :param pad_colour: Tuple - RGBA pad colour, for example (255, 0, 0, 255) is red. If
                       omitted then the colour is automatically allocated based on a
                       pixel in the image. Override pad_with_transparent

    :return: Scaled and padded image
    """
    dest_w = float(dest_w)
    dest_h = float(dest_h)
    dest_ratio = dest_w / dest_h

    # Calculate the apect ratio of the image
    src_w = float(image.size[0])
    src_h = float(image.size[1])
    src_ratio = src_w / src_h

    if src_ratio < dest_ratio:
        # Image is tall and thin - we need to scale to the right height and then pad
        scale = dest_h / src_h
        scaled_h = dest_h
        scaled_w = src_w * scale

        offset = (int((dest_w - scaled_w) / 2), 0)

    else:
        # Image is short and wide - we need to scale to the right height and then crop
        scale = dest_w / src_w
        scaled_w = dest_w
        scaled_h = src_h * scale

        offset = (0, int((dest_h - scaled_h) / 2))

    scaled_image = image.resize((int(scaled_w), int(scaled_h)), PIL.Image.ANTIALIAS)
    # Normally we will want to copy the source mode for the destination image, but in some
    # cases the source image will use a Palletted (mode=='P') in which case we need to change
    # the mode
    mode = scaled_image.mode
    log.debug('Padding image with mode: "{}"'.format(mode))
    if pad_with_transparent and mode != 'RGBA':
        old_mode = mode
        mode = 'RGBA'
        scaled_image = scaled_image.convert(mode)
        log.debug('Changed mode from "{}" to "{}"'.format(old_mode, mode))

    elif mode == 'P':
        if 'transparency' in scaled_image.info:
            mode = 'RGBA'
        else:
            mode = 'RGB'

        scaled_image = scaled_image.convert(mode)
        log.debug('Changed mode from "P" to "{}"'.format(mode))
    
    if not pad_colour:
        if pad_with_transparent:
            pad_colour = (255, 255, 255, 0)
        else:
            # Get the pixel colour for coordinate (0,0)
            pixels = scaled_image.load()
            pad_colour = pixels[0, 0]
    
    padded_image = PIL.Image.new(mode, (int(dest_w), int(dest_h)), pad_colour)
    padded_image.paste(scaled_image, offset)

    return padded_image


def resize_image_to_fit_width(image, dest_w):
    """
    Resize and image to fit the passed in width, keeping the aspect ratio the same

    :param image: PIL.Image
    :param dest_w: The desired width
    """
    scale_factor = dest_w / image.size[0]
    dest_h = image.size[1] * scale_factor
    
    scaled_image = image.resize((int(dest_w), int(dest_h)), PIL.Image.ANTIALIAS)

    return scaled_image


def resize_image_to_fit_height(image, dest_h):
    """
    Resize and image to fit the passed in height, keeping the aspect ratio the same

    :param image: PIL.Image
    :param dest_h: The desired height
    """
    scale_factor = dest_h / image.size[1]
    dest_w = image.size[0] * scale_factor
    
    scaled_image = image.resize((int(dest_w), int(dest_h)), PIL.Image.ANTIALIAS)

    return scaled_image


def image_to_bytes(image, format='PNG', quality=95):
    image_io = io.BytesIO()
    image.save(image_io, format=format, quality=quality)
    return image_io.getvalue()

