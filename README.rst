========
Thunagen
========


Google Cloud function to generate thumbnail for images in Google Storage.

Convention
----------

The thumbnails are placed in a folder "thumbnails" at the same place as original file.

The thumbnail size is appended to filename, right before the extention part. For example:


.. code-block::

    bucket
    └── folder
        ├── photo.jpg
        └── thumbnails
            ├── photo_128x128.jpg
            └── photo_512x512.jpg

The function expect these environment variables to be set:

- ``THUMB_SIZES``: Size of thumbnail to be generated. Example: ``512x512,128x128``.

- ``MONITORED_PATHS``: Folders (and theirs children) where the function will process the uploaded images. Muliple paths are separated by ":", like ``user-docs:user-profiles``.

The variables can be passed via *.env* file in the working directory.

Include to your project
-----------------------

Thunagen is provided without a *main.py* file, for you to easier incorporate to your project, where you may have your own way to configure deployment environment (different bucket for "staging" and "production", for example).

To include Thunagen, from your *main.py*, do:

.. code-block:: py

    from thunagen.functions import generate_gs_thumbnail
