import json
import time
from io import BytesIO
from pathlib import PurePosixPath
from typing import Dict
from datetime import datetime
from urllib.parse import quote_plus

import lazy_object_proxy
from logbook import Logger
from PIL import Image
from PIL import UnidentifiedImageError
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud.storage import Bucket
from google.cloud.exceptions import NotFound
from google.cloud.pubsub_v1.publisher.futures import Future
from google.api_core.exceptions import GoogleAPICallError, RetryError

from . import __version__
from .common import GCFContext, ImgSize, Thumbnail
from .conf import get_monitored_paths, get_thumbnail_sizes, should_notify


THUMB_SUBFOLDER = 'thumbnails'
TOPIC_PREFIX = 'thumbnail-generated'
logger = Logger(__name__)
# Lazily instantiate Google Cloud client, so that it won't break unittest
store = lazy_object_proxy.Proxy(storage.Client)   # type: storage.Client


def build_thumbnail_path(original: PurePosixPath, size: ImgSize) -> PurePosixPath:
    '''
    Build file path for thumbnail from original file.

    Example: abc/photo.jpg -> abc/photo_512x512.jpg
    The "orignal" argument has PurePosixPath type because the path is in Google Cloud Storage context,
    not neccessary a real filesytem path.
    '''
    ext = original.suffix
    folder = original.parent
    return folder / THUMB_SUBFOLDER / f'{original.stem}_{size}{ext}'


def upload(bucket: storage.Bucket, thumb: Thumbnail) -> bool:
    blob = bucket.blob(str(thumb.path))
    blob.upload_from_string(thumb.content, thumb.mimetype)
    logger.info('Uploaded {}.', thumb.path)
    # TODO: Copy ACL from original image
    blob.make_public()
    meta = {'Generator': f'Thunagen v{__version__}'}
    blob.metadata = meta
    blob.update()
    logger.debug('Made {} public and set metadata {}', thumb.path, meta)
    return True


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


def delete_thumbnails(bucket: Bucket, orpath: PurePosixPath):
    folder = orpath.parent
    prefix = folder / THUMB_SUBFOLDER / orpath.stem
    blobs = storage.list_blobs(bucket, prefix=str(prefix), fields='item(name)')
    bucket.delete_blobs(blobs, on_error=lambda b: logger.error('File {} seems to be deleted before.', b.name))


def notify_thumbnails_generated(project_id: str, original_path: str, generated: Dict[str, str]):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, quote_plus(f'{TOPIC_PREFIX}/{original_path}'))
    logger.debug('To publish to: {}', topic_path)
    try:
        publisher.create_topic(topic_path)
    except (GoogleAPICallError, RetryError) as e:
        logger.error('Failed to create topic {}. Error: {}', topic_path, e)
        return
    data = json.dumps(generated).encode()
    future = publisher.publish(topic_path, data)  # type: Future
    # Google Cloud's Future object cannot be checked with Python concurent.futures module
    for i in range(4):
        if future.done():
            break
        time.sleep(1)


def is_thumbnail_missing_or_obsolete(thumb_path: PurePosixPath, orig_updated_time: datetime, bucket: Bucket) -> bool:
    thumb_blob = bucket.get_blob(str(thumb_path))
    if not thumb_blob:
        return True
    return orig_updated_time > (thumb_blob.updated or thumb_blob.time_created)


def generate_gs_thumbnail(data: dict, context: GCFContext):
    '''Background Cloud Function to be triggered by Cloud Storage'''
    # For fields of data, look in: https://cloud.google.com/storage/docs/json_api/v1/objects#resource
    event_type = context.event_type
    if event_type != 'google.storage.object.finalize' and event_type != 'google.storage.object.delete':
        # Not the event we want
        return
    filepath = data['name']   # type: str
    monitored_paths = get_monitored_paths()
    # If root folder "/" is in watchlist, accept all path
    if not any(filepath.startswith(p) for p in monitored_paths) and '/' not in monitored_paths:
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
    file_last_uploaded = data['updated'] or data['timeCreated']
    try:
        orig = Image.open(BytesIO(filecontent))    # type: Image.Image
    except UnidentifiedImageError:
        logger.error('This image {} is not supported by Pillow.', filepath)
        return
    generated = {}
    for size in get_thumbnail_sizes():   # type: ImgSize
        planned_thumbpath = build_thumbnail_path(filepath, size)
        if not is_thumbnail_missing_or_obsolete(planned_thumbpath, file_last_uploaded, bucket):
            logger.info('Thumbnail {} already exists and newer than reported uploaded time {}. '
                        'Perhap some other cloud function created it. Skip.', planned_thumbpath, file_last_uploaded)
            continue
        thumb = create_thumbnail(orig, size, filepath)
        success = upload(bucket, thumb)
        if success:
            generated[str(size)] = str(thumb.path)
    project = store.project
    logger.debug('Thumbnails generated: {}', generated)
    if should_notify() and generated:
        original_path = f'{bucket.name}/{blob.name}'
        notify_thumbnails_generated(project, original_path, generated)
