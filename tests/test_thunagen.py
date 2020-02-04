import shutil
from pathlib import Path

import pytest
from PIL import Image

from thunagen.common import ImgSize
from thunagen.functions import create_thumbnail


testdata = (
    ('annie-spratt-NlcSjubZ9tM-unsplash.jpg', 'thumbnails/annie-spratt-NlcSjubZ9tM-unsplash_512x512.jpg'),
    # This file is missing extension
    ('patrick-hendry-CKFgnLGpWqc-unsplash', 'thumbnails/patrick-hendry-CKFgnLGpWqc-unsplash_512x512'),
)


@pytest.mark.parametrize('original_filename, thumbnail_path', testdata)
def test_create_thumbnail(original_filename, thumbnail_path, tmp_path):
    # Copy testing file to temp directory
    test_orig = Path(__file__).parent / 'annie-spratt-NlcSjubZ9tM-unsplash.jpg'
    main_path = Path(shutil.copy(str(test_orig), str(tmp_path)))
    size = ImgSize(512, 512)
    img = Image.open(main_path)
    # Call function and test
    thumb = create_thumbnail(img, size, main_path)
    thumb_path = str(thumb.path)
    assert thumb_path.endswith('thumbnails/annie-spratt-NlcSjubZ9tM-unsplash_512x512.jpg')
