import os
import boto
from logging import info
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat


class RemoteS3Files(object):

    def __init__(self, remote=dict()):
        # Establishing a new connection
        conn = boto.connect_s3(
            remote["access_key"], remote["secret_key"],
            is_secure=False, calling_format=OrdinaryCallingFormat()
        )
        # Connecting to the bucket
        self.bucket = conn.get_bucket(remote['bucket'], validate=True)
        # Setting remote configurations
        self.folder = remote['folder']

    def generate_presigned_url(self, key, expires_in=3600):
        # Capturing the required key
        key = self.bucket.new_key('%s/%s' % (self.folder, key))
        # Returning the temporary url
        return key.generate_url(
            expires_in=expires_in, query_auth=True)


def upload_to_s3(aws_access_key_id, aws_secret_access_key, file, bucket, key, callback=None, md5=None, reduced_redundancy=False, content_type=None):
    """
    Uploads the given file to the AWS S3
    bucket and key specified.

    callback is a function of the form:

    def callback(complete, total)

    The callback should accept two integer parameters,
    the first representing the number of bytes that
    have been successfully transmitted to S3 and the
    second representing the size of the to be transmitted
    object.

    Returns boolean indicating success/failure of upload.
    """
    try:
        size = os.fstat(file.fileno()).st_size
    except Exception as e:
        info(e)
        # Not all file objects implement fileno(),
        # so we fall back on this
        file.seek(0, os.SEEK_END)
        size = file.tell()

    conn = boto.connect_s3(aws_access_key_id, aws_secret_access_key, is_secure=False, calling_format=OrdinaryCallingFormat())
    bucket = conn.get_bucket(bucket, validate=True)
    k = Key(bucket)
    k.key = key
    if content_type:
        k.set_metadata('Content-Type', content_type)
    sent = k.set_contents_from_file(file, cb=callback, md5=md5, reduced_redundancy=reduced_redundancy, rewind=True)

    # Rewind for later use
    file.seek(0)

    if sent == size:
        return True
    return False


def s3_copy(aws_access_key_id, aws_secret_access_key, bucket, src, dst):
    try:
        conn = boto.connect_s3(aws_access_key_id, aws_secret_access_key, is_secure=False, calling_format=OrdinaryCallingFormat())
        bucket = conn.get_bucket(bucket, validate=True)
        bucket.copy_key(dst, bucket.name, src)
        return True
    except Exception as e:
        info(e)
        return False


def s3_delete(aws_access_key_id, aws_secret_access_key, bucket, key):
    try:
        conn = boto.connect_s3(aws_access_key_id, aws_secret_access_key, is_secure=False, calling_format=OrdinaryCallingFormat())
        bucket = conn.get_bucket(bucket, validate=True)
        k = Key(bucket=bucket, name=key)
        if k.exists():
            k.delete()
        if k.exists():
            return False
        else:
            return True
    except Exception as e:
        info(e)
        return False
