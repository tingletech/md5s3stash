FROM ubuntu:14.04
MAINTAINER "Brian Tingle <brian.tingle@ucop.edu>"

# Make sure the repos and packages are up to date
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y build-essential python python-dev python-setuptools python-pip python-numpy python-opencv libjpeg-dev libfreetype6-dev zlib1g-dev libwebp-dev liblcms2-dev

ADD requirements.txt .
ADD thumbnail.py .
ADD md5s3stash.py .

RUN pip install -r requirements.txt

EXPOSE 8888
CMD ["python", "thumbnail.py"]
