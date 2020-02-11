========
Thunagen
========


.. image:: https://madewithlove.now.sh/vn?heart=true&colorA=%23ffcd00&colorB=%23da251d
.. image:: https://badge.fury.io/py/thunagen.svg
   :target: https://pypi.org/project/thunagen/


Google Cloud function to generate thumbnail for images in Google Storage.

Convention
----------

The thumbnails are placed in a folder "thumbnails" at the same place as original file.

The thumbnail size is appended to filename, right before the extention part. For example:


.. code-block::

    bucket/
    └── folder/
        ├── photo.jpg
        └── thumbnails/
            ├── photo_128x128.jpg
            └── photo_512x512.jpg
        ├── photo-missing-extension
        └── thumbnails/
            ├── photo-missing-extension_128x128
            └── photo-missing-extension_512x512


The function expects these environment variables to be set:

- ``THUMB_SIZES``: Size of thumbnails to be generated. Example: ``512x512,128x128``.

- ``MONITORED_PATHS``: Folders (and theirs children) where the function will process the uploaded images. Muliple paths are separated by ":", like ``user-docs:user-profiles``. If you want to monitor all over the bucket, set it as ``/``.

- ``NOTIFY_THUMBNAIL_GENERATED`` (optional): Tell Thunagen to notify after thumbnails are created.

The variables can be passed via *.env* file in the working directory.

Get notified when thumbnails are generated
------------------------------------------

Other applications may want to be informed when the thumbnails are created. We support this by leveraging Google Cloud Pub/Sub service.

After finishing generating thumbnail, if the ``NOTIFY_THUMBNAIL_GENERATED`` environment variable is set (with non-empty value), the function will publish a message to Pub/Sub. The message is sent to topic ``thumbnail-generated/{bucket_name}/{image_path}``, with the content being JSON string of thumbnail info (size and path). Example:

- Topic: ``thumbnail-generated%2Fbucket%2Ffolder%2Fphoto.jpg`` (URL-encoded of "thumbnail-generated/bucket/folder/photo.jpg")

- Message:

    .. code-block:: json

        {
            "128x128": "folder/thumbnails/photo_128x128.jpg",
            "512x512": "folder/thumbnails/photo_512x512.jpg"
        }

Other applications can subscribe to that topic to get notified. Google doesnot allow slash ("/") in topic name, so subscribed applications have to take care of URL-encode, decode the topic.


Why Thunagen
------------

I'm aware that there is already a `Firebase extension <https://firebase.google.com/products/extensions/storage-resize-images>`_ for the same purpose.
But that extension, when doing its job, need to create a temporary file and in many cases, falling into race condition when the temporary file is deleted by another execution of the same cloud function. Thunagen, on the other hand, generates the file and uploads (back to Storage) on-the-fly (in memory), so it doesn't get into that issue.


Installation
------------

Thunagen is distributed via PyPI. You can install it with ``pip``::

    pip install thunagen


Include to your project
-----------------------

Thunagen is provided without a *main.py* file, for you to incorporate more easily to your project, where you may have your own way to configure deployment environment (different bucket for "staging" and "production", for example).

To include Thunagen, from your *main.py*, do:

.. code-block:: py

    from thunagen.functions import generate_gs_thumbnail


Credit
------

Thunagen is brought to you by `Nguyễn Hồng Quân <https://github.com/hongquan>`_, from SunshineTech (Việt Nam).
