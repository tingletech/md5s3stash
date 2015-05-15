md5s3stash
==========

![build status](https://travis-ci.org/ucldc/md5s3stash.svg)

content addressable storage in AWS S3

```
pip install https://github.com/ucldc/md5s3stash/archive/master.zip
```

Assumptions:

 * content on the web (url can be local file, however)
 * this is running in AWS on a machine with IAM role to write to the `BUCKET_BASE`
 * md5.hexdigest is used as the key to the file in the bucket

 * content is split into 36 buckets (`0-9a-z.BUCKET_BASE`) [see comments in code for details on why and how]  TODO: change this

 * mime/type is set, but image is not make public (actually, it is made public)

## Command line use

see `md5s3stash -h`
```
usage: md5s3stash [-h] [-b [BUCKET_BASE]] [-t TEMPDIR] [-w]
                  [--loglevel LOGLEVEL]
                  url [url ...]

content addressable storage in AWS S3

positional arguments:
  url                   URL or path of source file to stash

optional arguments:
  -h, --help            show this help message and exit
  -b [BUCKET_BASE], --bucket_base [BUCKET_BASE]
                        this must be a unique name in all of AWS S3
  -t TEMPDIR, --tempdir TEMPDIR
                        if your files might be large, make sure this is on a
                        big disk
  -w, --warnings        show python `DeprecationWarning`s supressed by default
  --loglevel LOGLEVEL

```

## Library use

see [the source](https://github.com/tingletech/md5s3stash/blob/master/md5s3stash.py)
for an example.  `md5s3stash`, `md5_to_s3_url`, and `md5_to_bucket_shard` probably most useful.

## Thumbnail server

```
# needed for Pillow (python image library) used by pilbox
brew install libtiff libjpeg webp little-cms2
```

[pilbox extension](http://agschwender.github.io/pilbox/#extension)
to generate thumbnails out of the md5s3stash.  Will run in elastic beanstalk
behind cloudfront.  Runs on `http://localhost:8888/` by default.

Only one URL pattern is supported `http://localhost:8888/{mode}/{width}x{height}/{md5}`

`mode` is `clip`, `crop`, `fill`, or `scale`


```
BUCKET_BASE=... thumbnail.py --position=face

python thumbnail.py --help
Usage: thumbnail_server [OPTIONS]

Options:

  --allowed_hosts                  valid hosts (default [])
  --allowed_operations             valid ops (default [])
  --background                     default hexadecimal bg color (RGB or ARGB)
  --client_key                     client key
  --client_name                    client name
  --config                         path to configuration file
  --content_type_from_image        override content type using image mime type
  --debug                          run in debug mode (default False)
  --expand                         default to expand when rotating
  --filter                         default filter to use when resizing
  --format                         default format to use when outputting
  --help                           show this help information
  --implicit_base_url              prepend protocol/host to url paths
  --max_requests                   max concurrent requests (default 40)
  --mode                           default mode to use when resizing
  --operation                      default operation to perform
  --optimize                       default to optimize when saving
  --port                           run on the given port (default 8888)
  --position                       default cropping position
  --quality                        default jpeg quality, 0-100
  --timeout                        request timeout in seconds (default 10)
  --validate_cert                  validate certificates (default True)

site-packages/tornado/log.py options:

  --log_file_max_size              max size of log files before rollover
                                   (default 100000000)
  --log_file_num_backups           number of log files to keep (default 10)
  --log_file_prefix=PATH           Path prefix for log files. Note that if you
                                   are running multiple tornado processes,
                                   log_file_prefix must be different for each
                                   of them (e.g. include the port number)
  --log_to_stderr                  Send log output to stderr (colorized if
                                   possible). By default use stderr if
                                   --log_file_prefix is not set and no other
                                   logging is configured.
  --logging=debug|info|warning|error|none 
                                   Set the Python log level. If 'none', tornado
                                   won't touch the logging configuration.
                                   (default info)

```

## Configuration

The `bucket_base` parameter, command line arguments `-b` and `--bucket_base`, and environmental variable `BUCKET_BASE`
must be unique name in all of AWS S3.  The IAM role or user will need to be able to create/write/read to 36 buckets
(`0-9a-z.BUCKET_BASE`).

## Development

md5s3stash has been tested on python 2.6 & 2.7.

python setup.py test

The test code has an example of using redis-collections as the caching dictionary.

To run a test of redis integration with the caching mechanism, set the environment variable LIVE_REDIS_TEST and have a redis server running locally.

Local redis with docker:

docker pull redis
docker run -p 6379:6379 --name md5-test -d redis
