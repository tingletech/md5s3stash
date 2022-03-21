FROM ubuntu:20.04
MAINTAINER "Brian Tingle <brian.tingle@ucop.edu>"

ARG DEBIAN_FRONTEND=noninteractive

# python 3.8
RUN apt-get update -y && \
  apt-get upgrade -y && \
  apt-get install -yq --no-install-recommends \
    build-essential \
    python3 \
    python3-dev \
    python3-numpy \
    python3-opencv \
    python3-pip \
    libcurl4-openssl-dev \
    libssl-dev \
    libfreetype6-dev \
    libjpeg-dev \
    liblcms2-dev \
    libmagic-dev \
    libwebp-dev \
    zlib1g-dev && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

ADD requirements-3.8.txt .
ADD thumbnail.py .

RUN python3 -m pip install -r requirements-3.8.txt
 
EXPOSE 8888
CMD ["python3", "thumbnail.py", "--position=face"]
