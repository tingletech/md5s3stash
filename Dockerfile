FROM ubuntu:14.04
MAINTAINER "Brian Tingle <brian.tingle@ucop.edu>"

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y build-essential
RUN apt-get install -y python python-dev python-setuptools python-pip
RUN apt-get install -y python-numpy python-opencv
RUN apt-get install -y libjpeg-dev libfreetype6-dev zlib1g-dev
RUN apt-get install -y libwebp-dev liblcms2-dev
RUN apt-get install -y git

RUN pip install git+git://github.com/tingletech/md5s3stash.git

EXPOSE 8888
CMD ["thumbnail_server"]
