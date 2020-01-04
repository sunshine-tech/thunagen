from io import BytesIO
from pathlib import PurePosixPath

import lazy_object_proxy
from logbook import Logger
from PIL import Image
from PIL import UnidentifiedImageError
from google.cloud import storage
from google.cloud.exceptions import NotFound

from .common import GCFContext, ImgSize, Thumbnail
from .conf import get_monitored_paths, get_thumbnail_sizes


THUMB_SUBFOLDER = 'thumbnails'
logger = Logger(__name__)
# Laziyly instantiate Google Cloud client, so that it won't break unittest
store = lazy_object_proxy.Proxy(storage.Client)   # type: storage.Client


def build_thumbnail_path(original: PurePosixPath, size: ImgSize) -> PurePosixPath:
    '''
    Build file path for thumbnail from original file.

    Example: abc/photo.jpg -> abc/photo_512x512.jpg
    The "orignal" argument has PurePosixPath type because the path is in Google Cloud Storage context,
    not neccessary be real filesytem path.
    '''
    ext = original.suffix
    folder = original.parent
    return folder / THUMB_SUBFOLDER / f'{original.stem}_{size}{ext}'


def upload(bucket: storage.Bucket, thumb: Thumbnail):
    blob = bucket.blob(str(thumb.path))
    blob.upload_from_string(thumb.content, thumb.mimetype)
    logger.info('Uploaded {}.', thumb.path)


def create_thumbnail(orig: Image.Image, size: ImgSize, orpath: PurePosixPath) -> Thumbnail:
    img = orig.copy()
    mimetype = orig.get_format_mimetype()
    img.thumbnail(size)
    out = BytesIO()
    img.save(out, orig.format)
    out.seek(0)
    thumbpath = build_thumbnail_path(orpath, size)
    logger.debug('Thumbnail path: {}', thumbpath)
    return Thumbnail(out.getvalue(), thumbpath, size, mimetype)


def delete_thumbnails(bucket: storage.Bucket, orpath: PurePosixPath):
    folder = orpath.parent
    prefix = folder / THUMB_SUBFOLDER / orpath.stem
    blobs = storage.list_blobs(bucket, prefix=str(prefix), fields='item(name)')
    bucket.delete_blobs(blobs, on_error=lambda b: logger.error('File {} seems to be deleted before.', b.name))


def generate_gs_thumbnail(data: dict, context: GCFContext):
    '''Background Cloud Function to be triggered by Cloud Storage'''
    event_type = context.event_type
    if event_type != 'google.storage.object.finalize' and event_type != 'google.storage.object.delete':
        # Not the event we want
        return
    filepath = data['name']   # type: str
    if not any(filepath.startswith(p) for p in get_monitored_paths()):
        logger.debug('File {} is not watched. Ignore.', filepath)
        return
    filepath = PurePosixPath(filepath)
    folder_name = filepath.parent.name
    if folder_name == THUMB_SUBFOLDER:
        logger.info('The file {} is already a thumbnail. Ignore.', filepath)
        return
    content_type = data['contentType']  # type: str
    if not content_type.startswith('image/'):
        logger.debug('The file {} is not an image (content type {}). Ignore.', filepath, content_type)
        return
    bucket = store.get_bucket(data['bucket'])
    if event_type == 'google.storage.object.delete':
        delete_thumbnails(bucket, filepath)
        return
    try:
        blob = bucket.get_blob(str(filepath))
    except NotFound:
        logger.error('File {} was deleted by another job.', filepath)
        return
    filecontent = blob.download_as_string()
    try:
        orig = Image.open(BytesIO(filecontent))    # type: Image.Image
    except UnidentifiedImageError:
        logger.error('This image {} is not supported by Pillow.', filepath)
        return
    for size in get_thumbnail_sizes():   # type: ImgSize
        thumb = create_thumbnail(orig, size, filepath)
        upload(bucket, thumb)
