FROM lahwran/crawler-base
MAINTAINER lahwran <lahwran0@gmail.com>

CMD ["coordinator", "--http-port", "8080", "--coord-port", "9090"]
EXPOSE 8080 9090
