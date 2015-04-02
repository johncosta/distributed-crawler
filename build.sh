#!/bin/bash

docker build -t lahwran/crawler . || exit 1
docker stop crawler-run || true
docker rm crawler-run || true
