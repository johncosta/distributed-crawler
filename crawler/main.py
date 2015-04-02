#!/usr/bin/env python
from __future__ import unicode_literals, print_function

import argparse


def main(node_type, coord_url=None):
    from twisted.internet import reactor

    if node_type not in [b"coordinator", b"drone"]:
        raise InvalidArguments("Please pick 'coordinator' or 'drone'.")
    elif node_type == b"drone_only" and coord_url is None:
        raise InvalidArguments("'coord_url' is required for drone-only nodes.")

    if node_type == b"drone_only":
        coordinator = drone.CoordinatorClient(coord_address, coord_port)

        reactor dot connect tcp or something
    else:
        server = central.CoordinatorServer()
        http_server = central.JobApiServer(server)
        # TODO: endpoints etc. also tls! tls with endpoints!
        reactor.listenTCP(http_port, http_server.to_factory())
        reactor.listenTCP(coord_port, server)

    drones = []
    for x in range(drone_count):
        drone = Drone(coordinator_client)
        drone.start()

        # it's not really necessary to keep track of them, as twisted will
        # do it for us, but it feels nicer.
        drones.append(drone)

    reactor.run()


parser = argparse.ArgumentParser(description="Yay, pictures!")
parser.add_argument(b"node_type",
        help="Node type - 'coordinator' or 'drone_only'")
parser.add_argument(b"coordinator_address", default=None,
        help="If node_type is 'drone', set this to the host:port of the "
             "coordinator.")
parser.add_argument(b"--worker-count", type=int, default=2,
        help="Number workers. That is, number of http requests to have "
                "in flight at once.")


class InvalidArguments(ValueError):
    pass


if __name__ == b"__main__":
    args = parser.parse_args()
    try:
        main(**vars(args))
    except InvalidArguments as e:
        print(str(e))
        print()
        parser.print_help()
