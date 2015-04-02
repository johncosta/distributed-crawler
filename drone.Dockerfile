FROM lahwran/crawler-base
MAINTAINER lahwran <lahwran0@gmail.com>

CMD ["drone", "--docker-link-alias", "coord"]
