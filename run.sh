#!/bin/bash

if ! ./build.sh >& /tmp/docker_output ; then
    cat /tmp/docker_output
    exit 1
fi
docker run -ti --name=crawler-run lahwran/crawler "$@"
