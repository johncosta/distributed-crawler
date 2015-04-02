import json
import random
import urlparse
import re
import itertools
from collections import deque

from twisted.internet.protocol import Factory
from twisted.web.server import Site
from klein import Klein

from crawler import util


class Job(object):
    def __init__(self, job_id):
        self.queue = deque()
        self.seen_urls = set()
        self.result_urls = set()
        self.id = job_id
        self.working_count = 0
        self.finished_count = 0

    def finished_one(self):
        self.working_count -= 1
        self.finished_count += 1

    def add_url(self, url, level=0):
        if url in self.seen_urls:
            return
        if level < 2:
            self.queue.append(util.QueueEntry(self.id, level, url))
            self.seen_urls.add(url)

        parsed = urlparse.urlparse(url)
        # why does match() match only the beginning, instead of the whole
        # string? I will never stop wondering (...even after I find out)
        if re.search(r'\.(gif|je?pg|png|bmp|webp)', parsed.path):
            self.result_urls.add(url)

    def pop_url(self):
        if not self.queue:
            return None

        self.working_count += 1
        return self.queue.popleft()


class CoordinatorSession(util.CommandProtocol):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.waiting = 0

    def connectionMade(self):
        self.coordinator.clients.append(self)
        self.waiting = self.coordinator.parallel_per_drone
        for x in range(self.waiting):
            self.send_one()

    def connectionLost(self, reason):
        self.coordinator.clients.remove(self)

    def message_found(self, url_info):
        # called no matter what kind of url - this just means there was a url
        # found by the drone
        queue_entry = util.queue_entry_parse(url_info)
        self.coordinator.found_url(queue_entry)

    def message_url_completed(self, job_id):
        self.waiting += 1
        self.send_one()
        job = self.coordinator.jobs[job_id]
        job.finished_one()

    def send_one(self, queue_entry=None):
        if queue_entry is None:
            queue_entry = self.coordinator.pop_url()
            if queue_entry is None:
                return

        self.waiting -= 1
        self.command("scan_url", util.queue_entry_format(queue_entry))


class CoordinatorServer(Factory):
    """
    The queue server/leader.

    I considered various other things I hadn't used before (zeromq, rabbitmq,
    celery, etc), especially in the hope that I could find an existing
    brokerless task queue (a not-fully-connected mesh network sort of layout
    would be really cool), but ended up deciding that that was too many new
    things to learn. http://mcfunley.com/choose-boring-technology

    So it's got some centralization that I'd rather not have. This will be a
    bottleneck that prevents unbounded scaling, which would have to be
    refactored into something fancier when that level of scale was reached.
    Google wouldn't be able to run off this crawler, unfortunately.

    I also considered having a database of some kind for the queue, but as I
    haven't used any databases I'd be happy with for this, I decided to just
    hack my own.

    Incidentally, I like to use the word "Server" for what twisted calls
    "factories", and "Session" for what twisted calls "protocols".
    """

    def __init__(self, parallel_per_drone):
        self.jobs = {}
        self.clients = []
        self.parallel_per_drone = parallel_per_drone

    def allocate_job(self):
        # this method adapted from tree-of-life/treeoflife/nodes/node.py
        for x in xrange(10):
            job_id = util.gen_id()
            if job_id in self.jobs:  # pragma: no cover
                continue

            job = self.jobs[job_id] = Job(job_id)
            return job

        else:  # pragma: no cover
            raise Exception("10 tries to generate node id failed. wat? this "
                            "really should be impossible. %s" % job_id)

    def found_url(self, queue_entry):
        # TODO: robots.txt parsing - has a bonus: sitemap.xml
        job = self.jobs[queue_entry.job_id]
        job.add_url(queue_entry.url, queue_entry.level)
        self._broadcast(job)

    def _broadcast(self, job):
        clients = [[client] * client.waiting for client in self.clients]
        for client in itertools.chain.from_iterable(clients):
            if not job.queue:
                break
            if client.waiting <= 0:
                continue
            client.send_one(job.pop_url())


    def pop_url(self):
        # this isn't efficient, but I'm wasting too much time overengineering
        # this silly project
        jobs = self.jobs.values()
        random.shuffle(jobs)
        for x in jobs:
            result = x.pop_url()
            if result is not None:
                return result

        return None

    def buildProtocol(self, addr):
        return CoordinatorSession(self)


class NotFound(Exception):
    pass


class JobApiServer(object):
    """
    Http service for the actual public api.

    This was originally going to be in CoordinatorServer, but that felt like
    too much in one class.
    """

    # I don't remember where it's documented that you can do this. Klein's
    # documentation kind of sucks. But I did it in another project, so I
    # pattern matched this code from there. It definitely works, and binds
    # to the instance. See Klein.__get__ in klein/app.py in klein's code.
    http = Klein()

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @http.route("/", methods=["POST"])
    def http_submit_urls(self, request):
        # urls can't have \n in them anymore. I say so. >:|
        #   (they actually can in real life, although few things support it.)
        #
        # also, for some reason, request.content is fully buffered before
        #   this method is called. seems odd of twisted to do it that way,
        #   but whatever. request is a t.w.s.Request.

        urls = (url for url in request.content.read().split("\n") if url)
        print
        print repr(urls)

        job = self.coordinator.allocate_job()
        for url in urls:
            print
            print "adding url", repr(url), type(url)
            print
            if type(url) == unicode:
                print "Unicode string!"
                url = url.encode("utf-8")
            job.add_url(url)
        self.coordinator._broadcast(job)

        return json.dumps(job.id) + '\n'

    def _job_status_info(self, job):
        return {
            "crawled_urls": {
                "finished": job.finished_count,
                "in_progress": job.working_count,
                "waiting_in_queue": len(job.queue)
            },
            "result_count": len(job.result_urls),
        }

    def get_job(self, job_id):
        try:
            return self.coordinator.jobs[job_id]
        except KeyError:
            raise NotFound

    @http.handle_errors(NotFound)
    def notfound(self, request, failure):
        request.setResponseCode(404)
        return 'No such job id'

    @http.route("/status/<job_id>")
    def http_job_status(self, request, job_id):
        job = self.get_job(job_id)
        return json.dumps(self._job_status_info(job))

    @http.route("/status/all")
    def http_job_all(self, request):
        result = {}
        for job_id, job in self.coordinator.jobs.items():
            result[job_id] = self._job_status_info(job)
        return json.dumps(result)

    @http.route("/result/<job_id>")
    def http_job_results(self, request, job_id):
        job = self.get_job(job_id)
        return json.dumps(list(job.result_urls))

    def to_factory(self):  # pragma: no cover
        return Site(self.http.resource())
