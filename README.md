md5s3stash
==========

content addressable storage in AWS S3

`BUCKET_BASE='base'`
  base string to use in bucket name

`BUCKET_DEPTH='2'`
  a depth of 2 will create 256 (16^2) buckets to split files between based on the first 2 characters of the checksum.
  
  "Consider utilizing multiple buckets that start with different alphanumeric characters. This will ensure a degree of partitioning from the start. The higher your volume of concurrent PUT and GET requests, the more impact this will likely have." -- http://aws.amazon.com/articles/1904?_encoding=UTF8&jiveRedirect=1

use base64 of the md5; rather than hex?  This would spread out the keys more.

for each file in arguments:

  - download the file locally if needed and take md5sum of file
  - upload file to the correct s3 bucket based on `BUCKET_BASE` and `BUCKET_DEPTH`

daemon mode:
  - watch an SQS queue and process URLs coming in


