#!/usr/bin/env python

import os
import argparse

from twisted.internet.protocol import ReconnectingClientFactory

from crawler import central
from crawler import drone


class CoordClientFactory(ReconnectingClientFactory):
    def buildProtocol(self, addr):
        self.resetDelay()
        return drone.CoordinatorClient()


def main(node_type, coord_addr=None, docker_link_alias=None,
        http_port=8080, coord_port=9090,
        parallel_per_drone=2):
    from twisted.internet import reactor

    if docker_link_alias is not None:
        alias = docker_link_alias.upper()
        coord_addr = "{}:{}".format(docker_link_alias.lower(),
                os.environ["{}_PORT_{}_TCP_PORT".format(alias, coord_port)])

    if node_type not in ["coordinator", "drone"]:
        raise InvalidArguments("Please pick 'coordinator' or 'drone'.")
    elif node_type == "drone" and coord_addr is None:
        raise InvalidArguments("'coord_addr' is required for drone nodes.")

    if node_type == "drone":
        host, _, port = coord_addr.partition(":")
        port = int(port)
        print("Connecting as drone to host {} port {}".format(host, port))
        reactor.connectTCP(host, port, CoordClientFactory())
    else:
        print("Setting up http://{HOSTNAME}:{}".format(http_port, **os.environ))
        print("Setting up coord://{HOSTNAME}:{}".format(coord_port, **os.environ))
        server = central.CoordinatorServer(parallel_per_drone)
        http_server = central.JobApiServer(server)
        # TODO: endpoints etc. also tls! tls with endpoints!
        reactor.listenTCP(http_port, http_server.to_factory())
        reactor.listenTCP(coord_port, server)

    reactor.run()


parser = argparse.ArgumentParser(description="Yay, pictures!")
parser.add_argument("node_type",
        help="Node type - 'coordinator' or 'drone_only'")
parser.add_argument("coord_addr", default=None, nargs='?',
        help="If node_type is 'drone', set this to the host:port of the "
             "coordinator.")
parser.add_argument("--docker-link-alias", default=None)
parser.add_argument("--parallel-per-drone", type=int, default=2,
        help="Number of http requests to have "
                "in flight at once on a single drone.")
parser.add_argument("--http-port", type=int, default=8080,
        help="Http listening port (only in coordinator mode).")
parser.add_argument("--coord-port", type=int, default=9090,
        help="Coord listening port (only in coordinator mode).")


class InvalidArguments(ValueError):
    pass


if __name__ == "__main__":
    args = parser.parse_args()
    try:
        main(**vars(args))
    except InvalidArguments as e:
        print(str(e))
        print()
        parser.print_help()
