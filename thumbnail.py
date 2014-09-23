#!/usr/bin/env python
""" thumbnail server for md5s3stash 
extension to pilbox server http://agschwender.github.io/pilbox/#extension
"""
import tornado.gen
from pilbox.app import PilboxApplication, ImageHandler, main
from md5s3stash import md5_to_http_url
import boto
import os


class ThumbnailApplication(PilboxApplication):
    def get_handlers(self):
        # URL regex to handler mapping
        return [(r"/([^/]+)/(\d+)x(\d+)/(.+)", ThumbnailImageHandler)]
        #            mode, w, h, md5


class ThumbnailImageHandler(ImageHandler):
    def prepare(self):
        self.args = self.request.arguments.copy()
        self.settings['content_type_from_image'] = True
        assert 'BUCKET_BASE' in os.environ, "`BUCKET_BASE` must be set"

    @tornado.gen.coroutine
    def get(self, mode, w, h, md5):
        
        url = md5_to_http_url(md5, os.environ['BUCKET_BASE'])
        self.args.update(dict(w=w, h=h, url=url))

        self.validate_request()
        self.settings['mode'] = mode
        resp = yield self.fetch_image()
        self.render_image(resp)

    def get_argument(self, name, default=None):
        return self.args.get(name, default)


if __name__ == "__main__":
    main(app=ThumbnailApplication())
