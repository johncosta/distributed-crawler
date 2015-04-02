from __future__ import unicode_literals, print_function

import string
import random
from collections import namedtuple

from twisted.internet.protocol import Protocol

QueueEntry = namedtuple('QueueEntry', ['job_id', 'level', 'url'])


class LineOnlyReceiver(Protocol):
    """
    This class is from github.com/lahwran/tree-of-life/treeoflife/protocols.py

    Copied-and-edited version of twisted LineOnlyReceiver.
    I DON'T WANT A LENGTH LIMIT
    """
    _buffer = b''
    delimiter = b'\n'

    def dataReceived(self, data):
        """Translates bytes into lines, and calls line_received."""
        lines = (self._buffer + data).split(self.delimiter)
        self._buffer = lines.pop(-1)
        for line in lines:
            if self.transport.disconnecting:
                # this is necessary because the transport may be told to lose
                # the connection by a line within a larger packet, and it is
                # important to disregard all the lines in that packet following
                # the one that told it to close.
                return
            self.line_received(line)

    def line_received(self, line):
        """Override this for when each line is received.
        """
        raise NotImplementedError

    def send_line(self, line):
        """Sends a line to the other end of the connection.
        """
        return self.transport.writeSequence((line, self.delimiter))


class CommandProtocol(LineOnlyReceiver):
    # just a cheap thing. would put it in LineOnlyReceiver if that wasn't
    # copied from elsewhere.
    def line_received(self, line):
        command, space, data = line.partition(b' ')

        # TODO: this will crash if the other end sends an
        # invalid message. this is trusting the remote computer!
        handler = getattr(self, b"message_%s" % command)

        handler(data)

    def command(self, command, args):
        self.send_line(b"{} {}".format(command, args))


def queue_entry_format(queue_entry):
    # a4b19 1 http://google.com/section with spaces/derp
    return b"{} {} {}".format(
            queue_entry.job_id,
            queue_entry.level,
            queue_entry.url.encode("utf-8"))


def queue_entry_parse(data):
    job_id, _, rest = data.partition(b' ')
    level, _, url = rest.partition(b' ')
    level = int(level)
    url = url.decode("utf-8")
    return QueueEntry(job_id, level, url)


def gen_id():
    id_chars = string.ascii_letters + string.digits
    return b"".join(random.choice(id_chars) for x in xrange(5))
