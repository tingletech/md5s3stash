#!/usr/bin/env python

import tornado.gen

from pilbox.app import PilboxApplication, ImageHandler, main


class CustomApplication(PilboxApplication):
    def get_handlers(self):
        return [(r"/(\d+)x(\d+)/(.+)", CustomImageHandler)]


class CustomImageHandler(ImageHandler):
    def prepare(self):
        self.args = self.request.arguments.copy()

    @tornado.gen.coroutine
    def get(self, w, h, url):
        self.args.update(dict(w=w, h=h, url=url))

        self.validate_request()
        resp = yield self.fetch_image()
        self.render_image(resp)

    def get_argument(self, name, default=None):
        return self.args.get(name, default)


if __name__ == "__main__":
    main(app=CustomApplication())
