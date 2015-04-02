#!/bin/bash

docker build -t lahwran/crawler . || exit 1
docker stop crawler-run
docker rm crawler-run
