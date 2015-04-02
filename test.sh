#!/bin/bash

./run.sh py.test --cov-report html --cov crawler --color=no -v || exit
docker cp crawler-run:/app/htmlcov /tmp/
rm -rf htmlcov >& /dev/null
mv /tmp/htmlcov .
