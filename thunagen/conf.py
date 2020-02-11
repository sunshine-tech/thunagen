import os
from typing import Tuple

from dotenv import load_dotenv, find_dotenv

from .common import ImgSize


load_dotenv(find_dotenv(usecwd=True))


def get_thumbnail_sizes() -> Tuple[ImgSize, ...]:
    var = os.getenv('THUMB_SIZES')
    if not var:
        return ()
    sizes = []
    for p in var.split(','):
        spec = p.strip()
        try:
            w, h = spec.split('x')
        except ValueError:
            continue
        try:
            sizes.append(ImgSize(int(w), int(h)))
        except ValueError:
            continue
    return tuple(sizes)


def get_monitored_paths() -> Tuple[str, ...]:
    var = os.getenv('MONITORED_PATHS')
    if not var:
        return ()
    configured_paths = tuple(p for p in var.split(':') if p)
    # If '/' (root) appears in list of paths, return only it.
    if '/' in configured_paths:
        return ('/',)
    return configured_paths


def should_notify() -> bool:
    return bool(os.getenv('NOTIFY_THUMBNAIL_GENERATED'))
