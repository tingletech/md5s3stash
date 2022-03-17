#!/usr/bin/env python
""" thumbnail server for md5s3stash
extension to pilbox server http://agschwender.github.io/pilbox/#extension
"""
import tornado.gen
from pilbox.app import PilboxApplication, ImageHandler, main
import os


assert 'BUCKET_BASE' in os.environ, "`BUCKET_BASE` must be set"


def md5_to_http_url(md5, bucket_base, bucket_scheme='multibucket', s3_endpoint='s3.amazonaws.com'):
    """ calculate the http URL given an md5 and an bucket_base """
    if bucket_scheme == 'simple':
        url = "http://{0}/{1}/{2}".format(
            s3_endpoint,
            bucket_base,
            md5
        )
    elif bucket_scheme == 'multibucket':
        url = "http://{1}.{2}.{0}/{3}".format(
            s3_endpoint,
            md5_to_bucket_shard(md5),
            bucket_base,
            md5
        )
    return url


class ThumbnailApplication(PilboxApplication):
    def get_handlers(self):
        # URL regex to handler mapping
        return [
            (r"^/([^/]+)/(\d+)x(\d+)/([a-fA-F\d]{32})$", ThumbnailImageHandler),
            (r"^/([^/]+)/(\d+)x(\d+)/.*$", ThumbnailImageHandler)
        ]
        #            mode, w, h, md5


class ThumbnailImageHandler(ImageHandler):
    def prepare(self):
        self.args = self.request.arguments.copy()
        self.settings['content_type_from_image'] = True

    @tornado.gen.coroutine
    def get(self, mode, w, h, md5='0d6cc125540194549459df758af868a8'):
        url = md5_to_http_url(
            md5,
            os.environ['BUCKET_BASE'],
            bucket_scheme=os.getenv('BUCKET_SCHEME', 'multibucket'),
            s3_endpoint=os.getenv('S3_ENDPOINT'),
        )
        self.args.update(dict(w=w, h=h, url=url, mode=mode))
        self.validate_request()
        resp = yield self.fetch_image()
        resp.headers["Cache-Control"] = "public, max-age=31536000"
        self.render_image(resp)


    def get_argument(self, name, default=None):
        return self.args.get(name, default)


if __name__ == "__main__":
    main(app=ThumbnailApplication(timeout=30,))
