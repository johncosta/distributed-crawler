#!/bin/bash

docker build -t lahwran/crawler-base . && \
docker build -t lahwran/crawler-coord -f coord.Dockerfile . && \
docker build -t lahwran/crawler-drone -f drone.Dockerfile . && \
docker build -t lahwran/crawler-curl -f curl.Dockerfile .
