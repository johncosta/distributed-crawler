from __future__ import unicode_literals, print_function

from StringIO import StringIO
import json

import pytest

from crawler import central
from crawler import util

def test_coordinator_allocate():
    coord = central.CoordinatorServer(1)

    job = coord.allocate_job()
    assert len(job.id) == 5
    assert type(job.id) == str
    assert not len(job.queue)
    assert not len(job.result_urls)
    assert not len(job.seen_urls)
    assert job.working_count == 0
    assert job.finished_count == 0


@pytest.fixture()
def four_urls_str():
    return (
        b"http://google.com\n"
        b"http://anotherurl.com\n"
        b"http://www.com\n"
        b"http://com.google\n"
    )


class PostRequest(object):
    def __init__(self, content):
        assert type(content) == str
        self.content = StringIO(content)


class GetRequest(object):
    def setResponseCode(self, code):
        self.code = code


def test_job_response(four_urls_str):
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    response = http.http_submit_urls(PostRequest(four_urls_str))

    assert json.loads(response) == coord.jobs.keys()[0]


class NoIOSession(central.CoordinatorSession):
    def __init__(self, *a, **kw):
        # would use super, but inheriting from protocol means old-style class
        central.CoordinatorSession.__init__(self, *a, **kw)

        self.mqueue = []
        assert not self.waiting

    def send_line(self, line):
        self.mqueue.append(line)

    def _drain(self):
        mq = self.mqueue
        self.mqueue = []
        assert all(type(x) == str for x in mq)
        return mq


def test_job_broadcast(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()
    assert coord.clients == clients

    http.http_submit_urls(PostRequest(four_urls_str))

    for url, client in zip(four_urls_str.strip().split(), coord.clients[:4]):
        assert client._drain() == [
            b"scan_url abcde 0 " + url
        ]
        assert not client.waiting

    assert coord.clients[-1].waiting
    assert not coord.clients[-1]._drain()
    assert not len(coord.jobs["abcde"].queue)


def test_too_many_urls_broadcast(four_urls_str, monkeypatch):
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    job_id_0 = json.loads(http.http_submit_urls(PostRequest(four_urls_str)))
    job_id_1 = json.loads(http.http_submit_urls(PostRequest(four_urls_str)))

    for url, client in zip(four_urls_str.strip().split()[:2],
                           coord.clients[4:]):
        assert client._drain() == [
            b"scan_url {} 0 {}".format(job_id_1, url)
        ]
        assert not client.waiting

    assert not len(coord.jobs[job_id_0].queue)
    assert len(coord.jobs[job_id_1].queue) == 2


def test_result_url(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    http.http_submit_urls(PostRequest(four_urls_str))

    for url, client in zip(four_urls_str.strip().split(), coord.clients):
        assert client._drain() == [b"scan_url abcde 0 {}".format(url)]
        assert not client.waiting

    assert coord.jobs["abcde"].working_count == 4
    assert coord.jobs["abcde"].finished_count == 0

    coord.clients[0].line_received("url_completed abcde")
    coord.clients[0].line_received("found abcde 1 http://derp.com")
    coord.clients[0].line_received("found abcde 1 http://derp.com/asdf.jpg")
    coord.clients[1].line_received("url_completed abcde")
    coord.clients[1].line_received("found abcde 1 http://blah.com")

    assert len(coord.jobs["abcde"].seen_urls) == 7
    assert len(coord.jobs["abcde"].result_urls) == 1
    assert coord.jobs["abcde"].finished_count == 2
    assert coord.jobs["abcde"].working_count == 4


def test_get_status(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    http.http_submit_urls(PostRequest(four_urls_str))

    for client in coord.clients:
        client._drain()

    coord.clients[0].line_received("url_completed abcde")
    coord.clients[0].line_received("found abcde 1 http://derp.com")
    coord.clients[0].line_received("found abcde 1 http://google.com")
    coord.clients[0].line_received("found abcde 1 http://derp.com/asdf.jpg")
    coord.clients[0].line_received("found abcde 1 http://derp.com/herp.gif")
    coord.clients[1].line_received("url_completed abcde")
    coord.clients[1].line_received("found abcde 1 http://blah.com")

    
    req = GetRequest()
    assert json.loads(http.http_job_status(req, b"abcde")) == {
        "crawled_urls": {
            "finished": 2,
            "in_progress": 4,
            # note: it adds probably-image urls to be scanned. this is
            # only necessary if we're going to do mimetype checking, which
            # we're not.
            "waiting_in_queue": 2,
        },
        "result_count": 2
    }

    req = GetRequest()
    assert sorted(json.loads(http.http_job_results(req, b"abcde"))) == [
        "http://derp.com/asdf.jpg",
        "http://derp.com/herp.gif",
    ]


def test_client_later_connect(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    http.http_submit_urls(PostRequest(four_urls_str))

    clients.extend([
        NoIOSession(coord),
        NoIOSession(coord),
    ])
    for client in clients[2:]:
        client.connectionMade()


    for url, client in zip(four_urls_str.strip().split(), coord.clients[:4]):
        assert client._drain() == [
            b"scan_url abcde 0 " + url
        ]
        assert not client.waiting

    assert not len(coord.jobs["abcde"].queue)


def test_max_depth(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    http.http_submit_urls(PostRequest(four_urls_str))

    for client in clients:
        client._drain()

    coord.clients[0].line_received("url_completed abcde")
    coord.clients[1].line_received("url_completed abcde")
    coord.clients[2].line_received("url_completed abcde")
    coord.clients[3].line_received("url_completed abcde")

    assert all(client.waiting == 1 for client in clients)

    coord.clients[0].line_received("found abcde 1 http://derp.com")
    coord.clients[0].line_received("found abcde 1 http://derp.com/asdf.jpg")
    coord.clients[1].line_received("found abcde 1 http://blah.com")

    assert clients[0].waiting == 0
    assert clients[1].waiting == 0
    assert clients[2].waiting == 0

    assert clients[0]._drain() == ["scan_url abcde 1 http://derp.com"]
    assert clients[1]._drain() == ["scan_url abcde 1 http://derp.com/asdf.jpg"]
    assert clients[2]._drain() == ["scan_url abcde 1 http://blah.com"]

    coord.clients[0].line_received("url_completed abcde")
    coord.clients[0].line_received("found abcde 2 http://deeper.com")
    coord.clients[0].line_received("found abcde 2 http://deeper.com/asdf.jpg")
    coord.clients[1].line_received("url_completed abcde")
    coord.clients[1].line_received("found abcde 2 http://deeperer.com")
    coord.clients[2].line_received("url_completed abcde")

    assert all([client.waiting == 1 for client in clients])

    assert len(coord.jobs["abcde"].seen_urls) == 7
    assert len(coord.jobs["abcde"].result_urls) == 2
    assert coord.jobs["abcde"].finished_count == 7
    assert coord.jobs["abcde"].working_count == 0

def test_max_depth_max_parallel(four_urls_str, monkeypatch):
    monkeypatch.setattr(util, 'gen_id', lambda: "abcde")
    coord = central.CoordinatorServer(4)
    http = central.JobApiServer(coord)

    clients = [
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
        NoIOSession(coord),
    ]
    for client in clients:
        client.connectionMade()

    http.http_submit_urls(PostRequest(four_urls_str))

    assert clients[0]._drain() == [
        "scan_url abcde 0 http://google.com",
        "scan_url abcde 0 http://anotherurl.com",
        "scan_url abcde 0 http://www.com",
        "scan_url abcde 0 http://com.google",
    ]
    for client in clients[1:]:
        assert client._drain() == []

    for x in range(4):
        coord.clients[0].line_received("url_completed abcde")

    assert all(client.waiting == 4 for client in clients)

    coord.clients[0].line_received("found abcde 1 http://derp.com")
    coord.clients[0].line_received("found abcde 1 http://derp.com/asdf.jpg")
    coord.clients[0].line_received("found abcde 1 http://blah.com")

    assert clients[0].waiting == 1

    # TODO: it doesn't balance between the clients very well when there
    # aren't enough jobs to keep the system saturated. Could add random.shuffle
    # in broadcast to fix this, but that would make testing more difficult.
    # I might fix it tomorrow, I can feel my brain not-working. Midnight code.

    assert clients[0]._drain() == [
        "scan_url abcde 1 http://derp.com",
        "scan_url abcde 1 http://derp.com/asdf.jpg",
        "scan_url abcde 1 http://blah.com"
    ]

    coord.clients[0].line_received("url_completed abcde")
    coord.clients[0].line_received("found abcde 2 http://deeper.com")
    coord.clients[0].line_received("found abcde 2 http://deeper.com/asdf.jpg")
    coord.clients[0].line_received("url_completed abcde")
    coord.clients[0].line_received("found abcde 2 http://deeperer.com")
    coord.clients[0].line_received("url_completed abcde")

    assert all([client.waiting for client in clients])

    assert len(coord.jobs["abcde"].seen_urls) == 7
    assert len(coord.jobs["abcde"].result_urls) == 2
    assert coord.jobs["abcde"].finished_count == 7
    assert coord.jobs["abcde"].working_count == 0


def test_get_nonexistant_job():
    coord = central.CoordinatorServer(1)
    http = central.JobApiServer(coord)

    req = GetRequest()
    with pytest.raises(central.NotFound) as err:
        http.http_job_status(req, "404me")

    assert http.notfound(req, err) == "No such job id"
    assert req.code == 404
