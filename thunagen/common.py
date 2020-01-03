from dataclasses import dataclass
from typing import NamedTuple
from pathlib import PurePosixPath


class GCFContext:
    '''Just a fake type, to help auto-completion in IDE.
    The real type is 'google.cloud.functions_v1.context.Context', which only exists
    when the function is run inside Google Cloud Function runtime.
    '''
    # Ex: 83006d7a-af1b-4833-8bc4-ab4ac8a374f9-0
    event_id: str
    # Ex: 2019-12-14T10:18:29.911055Z
    timestamp: str
    # Ex: google.storage.object.finalize
    event_type: str
    resource: str


class ImgSize(NamedTuple):
    width: int
    height: int

    def __str__(self):
        return f'{self.width}x{self.height}'


@dataclass
class Thumbnail:
    content: bytes
    path: PurePosixPath
    size: ImgSize
    mimetype: str
