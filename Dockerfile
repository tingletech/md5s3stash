FROM ubuntu:16.04
MAINTAINER "Brian Tingle <brian.tingle@ucop.edu>"

RUN apt-get update -y && \
  apt-get upgrade -y && \
  apt-get install -yq --no-install-recommends \
    build-essential \
    python \
    python-dev \
    python-numpy \
    python-opencv \
    python-pip \
    python-setuptools \
    libcurl4-openssl-dev \
    libssl-dev \
    libfreetype6-dev \
    libjpeg-dev \
    liblcms2-dev \
    libwebp-dev \
    zlib1g-dev && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

ADD requirements.txt .
ADD thumbnail.py .
ADD md5s3stash.py .

RUN pip install -r requirements.txt
 
EXPOSE 8888
CMD ["python", "thumbnail.py", "--position=face"]
