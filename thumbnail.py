#!/usr/bin/env python
""" thumbnail server for md5s3stash 
extension to pilbox server http://agschwender.github.io/pilbox/#extension
"""
import tornado.gen
from pilbox.app import PilboxApplication, ImageHandler, main
from md5s3stash import md5_to_s3_url
import boto


class ThumbnailApplication(PilboxApplication):
    def get_handlers(self):
        # URL regex to handler mapping
        return [(r"/(\d+)x(\d+)/(.+)/(.+)", ThumbnailImageHandler)]
        #            w, h, bucket_base, md5


class ThumbnailImageHandler(ImageHandler):
    def prepare(self):
        # TODO: default to clip, discard all other arguments
        self.args = self.request.arguments.copy()

    @tornado.gen.coroutine
    def get(self, w, h, bucket_base, md5):
        uri = md5_to_s3_url(md5, bucket_base)
        bucket_name, key_name = uri[len('s3://'):].split('/', 1)
        c = boto.connect_s3()
        bucket = c.get_bucket(bucket_name)
        key = bucket.get_key(key_name)
        self.args.update(dict(w=w, h=h, url=url))
        # validate max size?
        self.validate_request()
        self.render_image(key)

    def get_argument(self, name, default=None):
        return self.args.get(name, default)

    def _validate_url(self):
        url = self.get_argument("url")
        if not url:
            raise errors.UrlError("Missing url")
        elif url.startswith("s3://"):
            return
        raise errors.UrlError("Unsupported protocol")


if __name__ == "__main__":
    main(app=ThumbnailApplication())
