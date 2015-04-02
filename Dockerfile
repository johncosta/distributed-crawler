FROM ubuntu:14.04
MAINTAINER lahwran <lahwran0@gmail.com>

# Install python and twisted

RUN apt-get update && apt-get -y install -q \
    build-essential \
    python-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev

COPY get-pip.py /tmp/get-pip.py
# There seems to be a bug with using chmod in the same command:
# https://github.com/docker/docker/issues/9547
RUN chmod +x /tmp/get-pip.py
RUN /tmp/get-pip.py && \
    rm /tmp/get-pip.py

# Install app dependencies
COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

COPY . /app/

WORKDIR /app/

ENTRYPOINT ["/usr/bin/python", "-m", "crawler.main"]
CMD ["--help"]
