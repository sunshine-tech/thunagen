import shutil
from pathlib import Path

from PIL import Image

from thunagen.common import ImgSize
from thunagen.functions import create_thumbnail


def test_create_thumbnail(tmp_path):
    # Copy testing file to temp directory
    test_orig = Path(__file__).parent / 'annie-spratt-NlcSjubZ9tM-unsplash.jpg'
    main_path = Path(shutil.copy(str(test_orig), str(tmp_path)))
    size = ImgSize(512, 512)
    img = Image.open(main_path)
    # Call function and test
    thumb = create_thumbnail(img, size, main_path)
    thumb_path = str(thumb.path)
    assert thumb_path.endswith('thumbnails/annie-spratt-NlcSjubZ9tM-unsplash_512x512.jpg')
