md5s3stash
==========

content addressable storage in AWS S3

```
pip install https://github.com/tingletech/md5s3stash/archive/master.zip
```

Assumptions:

 * content on the web (url can be local file, however)
 * this is running in AWS on a machine with IAM role to write to the `BUCKET_BASE`
 * md5.hexdigest is used as the key to the file in the bucket
 * content is split into 36 buckets (`0-9a-z.BUCKET_BASE`) [see comments in code for details on why and how]
 * mime/type is set, but image is not make public

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
for an example.  `md5s3stash`, `md5_to_s3_url`, and `md5_to_bucket` probably most useful.

## Configuration

The `bucket_base` parameter, command line arguments `-b` and `--bucket_base`, and environmental variable `BUCKET_BASE`
must be unique name in all of AWS S3.  The IAM role or user will need to be able to create/write/read to 36 buckets
(`0-9a-z.BUCKET_BASE`).
