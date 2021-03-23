FROM ubuntu:14.04
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
    libfreetype6-dev \
    libjpeg-dev \
    liblcms2-dev \
    libwebp-dev \
    zlib1g-dev \
    curl \
    wget && \
 apt-get clean && \
 rm -rf /var/lib/apt/lists/*

ADD requirements.txt .
ADD thumbnail.py .
ADD md5s3stash.py .

RUN wget https://files.pythonhosted.org/packages/d8/f3/413bab4ff08e1fc4828dfc59996d721917df8e8583ea85385d51125dceff/pip-19.0.3-py2.py3-none-any.whl && \
  pip install pip-19.0.3-py2.py3-none-any.whl && \
  rm pip-19.0.3-py2.py3-none-any.whl
RUN python -m pip --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org install -r requirements.txt
 
EXPOSE 8888
CMD ["python", "thumbnail.py", "--position=face"]
