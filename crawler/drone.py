import urlparse

import lxml.etree
from twisted.internet import defer
import treq

from crawler import util

# from http://stackoverflow.com/a/2725168/1102705 plus a little research to
# categorize the strange tags
#
# certain images (could be more clever by always treating these as images, even
# when the extension mismatches. cheaper than mime type checking):
#     <body background=url>
#     <img src=url>
#     <input src=url>

# links off the page (some are unlikely to be html, but whatever, it's
# midnight):
#     <frame src=url>
#     <iframe src=url>
#
#     <a href=url>
#     <link href=url>
#
#     <blockquote cite=url>
#     <del cite=url>
#     <ins cite=url>
#     <q cite=url>

# media besides images:
#     <img usemap=url>
#     <area href=url>
#     <audio src=url>
#     <video poster=url> and <video src=url>
#     <source src=url>

# change semantics:
#     <base href=url>

# not relevant:
#     <frame longdesc=url>
#     <iframe longdesc=url>
#     <img longdesc=url>
#     <command icon=url>
#     <object classid=url>
#     <object codebase=url>
#     <object data=url>
#     <object usemap=url>
#     <button formaction=url>
#     <embed src=url>
#     <applet codebase=url>
#     <html manifest=url>
#     <head profile=url>
#     <script src=url>
#     <input formaction=url>
#     <form action=url>

class CoordinatorClient(util.CommandProtocol):
    def __init__(self):
        pass

    @defer.inlineCallbacks
    def message_scan_url(self, url_info):
        # I'm still not sure whether I like inlineCallbacks. It made
        # this easier to test, though, because of implicit maybeDeferred.

        # TODO: limit size of retrieved content. it could be huge!

        queue_entry = util.queue_entry_parse(url_info)

        response = yield treq.get(queue_entry.url)
        content = yield treq.content(response)

        base_url, urls = self.scan_page(queue_entry.url, content)
        urls = self.normalize_urls(base_url, urls)

        self.command("url_completed", queue_entry.job_id)
        for url in urls:
            # blah, QueueEntry feels like java
            qe = util.QueueEntry(queue_entry.job_id, queue_entry.level + 1, url)
            self.command("found", util.queue_entry_format(qe))

    def normalize_urls(self, base_url, urls):
        return [urlparse.urljoin(base_url, url) for url in urls]

    def scan_page(self, base_url, content):
        # TODO: switch parser based on whether it's xhtml or html
        # TODO: this could be optimized a *lot*, lots of redundant operations
        result = []

        xml = lxml.etree.HTML(content)
        bases = xml.xpath("//base")
        for base in bases:
            href = base.get("href")
            if href is None:
                continue
            result.append(href)
            base_url = href

        elementattrs = {
            "body": "background",
            "img": "src",
            "input": "src",

            "frame": "src",
            "iframe": "src",

            "a": "href",
            "link": "href",

            "blockquote": "cite",
            "del": "cite",
            "ins": "cite",
            "q": "cite",
        }
        xpath = " | ".join("//" + x for x in elementattrs.keys())
        for element in xml.xpath(xpath):
            attr = elementattrs[element.tag]
            val = element.get(attr)
            if val is not None:
                result.append(val)

        return base_url, result
