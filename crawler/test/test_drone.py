from __future__ import unicode_literals, print_function

import treq

from crawler import drone

webbernet = {
    "https://www.youtube.com/watch?v=_s9hIs0wYFQ": [
        "https://yt3.ggpht.com/-oN9IKkSVPkk/AAAAAAAAAAI/AAAAAAAAAAA/spfolhbKKLY/s88-c-k-no/photo.jpg",
        "https://i.ytimg.com/vi_webp/ZmA_Fwxucfw/default.webp",
        "/channel/UC5h2c7VrcFaHLM3HjxusG8g",
        "/",
        "https://s.ytimg.com/yts/img/pixel-vfl3z5WfW.gif",
        "watch?v=mfJC34tOZms",
    ],
    "https://www.youtube.com/": [
        "https://i.ytimg.com/vi_webp/JF0rsRLYkxc/mqdefault.webp",
        "https://www.youtube.com/watch?v=JF0rsRLYkxc",
        "https://www.youtube.com/user/MusicTranceMr",
        "https://yt3.ggpht.com/-KaOunkYkbGM/AAAAAAAAAAI/AAAAAAAAAAA/J8En5dobEgI/s88-c-k-no/photo.jpg",
        "https://yt3.ggpht.com/-oN9IKkSVPkk/AAAAAAAAAAI/AAAAAAAAAAA/spfolhbKKLY/s88-c-k-no/photo.jpg",
        "https://yt3.ggpht.com/-xc9WTkuv454/AAAAAAAAAAI/AAAAAAAAAAA/N2psDx66G9Q/s88-c-k-no/photo.jpg",
        "https://i.ytimg.com/vi/_DCJNWMtDio/mqdefault.jpg",
        "https://www.youtube.com/watch?v=_DCJNWMtDio",
    ],
    "https://www.youtube.com/channel/UC5h2c7VrcFaHLM3HjxusG8g": [
        "https://www.youtube.com/watch?v=mfJC34tOZms",
        "https://www.youtube.com/user/MusicTranceMr/videos",
        "https://www.youtube.com/playlist?list=WL",
        "https://www.youtube.com/watch?v=x9f9b5yMjmM",
        "https://i.ytimg.com/vi_webp/x9f9b5yMjmM/mqdefault.webp",
        "https://i.ytimg.com/vi_webp/SlEH5LK1OYA/mqdefault.webp",
        "https://yt3.ggpht.com/-ON3HbogHE54/AAAAAAAAAAI/AAAAAAAAAAA/rBwvXNXg4Wc/s88-c-k-no/photo.jpg",
        "https://yt3.ggpht.com/-bp-G-1ubrMA/AAAAAAAAAAI/AAAAAAAAAAA/lysFIFc6AaQ/s88-c-k-no/photo.jpg",
        "https://yt3.ggpht.com/-6QE1YI19yTU/AAAAAAAAAAI/AAAAAAAAAAA/SGwtv-BUKBs/s88-c-k-no/photo.jpg",
    ]
}


class NoIOSession(drone.CoordinatorClient):
    def __init__(self, *a, **kw):
        # would use super, but inheriting from protocol means old-style class
        drone.CoordinatorClient.__init__(self, *a, **kw)

        self.mqueue = []

    def send_line(self, line):
        self.mqueue.append(line)

    def _drain(self):
        mq = self.mqueue
        self.mqueue = []
        assert all(type(x) == str for x in mq)
        return mq


def test_client_communicate(monkeypatch):
    # also tests that urlparse.urljoin does what I thought it did (it does)

    session = NoIOSession()

    monkeypatch.setattr(drone.CoordinatorClient, "scan_page",
            lambda self, url, content: (url, webbernet[url]))
    monkeypatch.setattr(treq, "get", lambda x: None)
    monkeypatch.setattr(treq, "content", lambda x: None)

    session.line_received(b"scan_url abcde 0 "
                          b"https://www.youtube.com/watch?v=_s9hIs0wYFQ")

    assert session.mqueue[0] == "url_completed abcde"
    assert set(session.mqueue[1:]) == set([
        b"found abcde 1 https://yt3.ggpht.com/-oN9IKkSVPkk/AAAAAAAAAAI/AAAAAAAAAAA/spfolhbKKLY/s88-c-k-no/photo.jpg",
        b"found abcde 1 https://i.ytimg.com/vi_webp/ZmA_Fwxucfw/default.webp",
        b"found abcde 1 https://www.youtube.com/channel/UC5h2c7VrcFaHLM3HjxusG8g",
        b"found abcde 1 https://www.youtube.com/",
        b"found abcde 1 https://s.ytimg.com/yts/img/pixel-vfl3z5WfW.gif",
        b"found abcde 1 https://www.youtube.com/watch?v=mfJC34tOZms",
    ])


def test_page_parse_simple():
    session = NoIOSession()

    page = """
        <html>
            <head>
                <link href="some_css_thing.css"
                    ref="stylesheet" type="text/css">
            </head>
            <body background="http://image-at-root.com/">
                <a href="http://urlone.com/asdf">this is a place that is onthe thing</a>
                <img src="/derp_doesnt_look_like_an_image_link">
                <input src="/icons/derp.gif">
                <ins cite="http://somebody-distinguished.com/">asf</ins>
                <blockquote cite="http://another-somebody.com/">herp derp</blockquote>
                <del cite="http://someone-incompetent.net/">blah</del>
                <q cite="http://quote-from-someone.net/george-washing-tub/">zzz</q>
                <frame src="http://internet.net/this-isnt-how-frames-work.html"></frame>
                <iframe src="http://microsoft.com/iframes-actually-work-this-way.html"></frame>
            </body>
        </html>
    """

    base_url, urls = session.scan_page("http://base_url.com/", page)

    assert base_url == "http://base_url.com/"
    assert set(urls) == set([
        "some_css_thing.css",
        "http://image-at-root.com/",
        "http://urlone.com/asdf",
        "/derp_doesnt_look_like_an_image_link",
        "/icons/derp.gif",
        "http://somebody-distinguished.com/",
        "http://another-somebody.com/",
        "http://someone-incompetent.net/",
        "http://quote-from-someone.net/george-washing-tub/",
        "http://internet.net/this-isnt-how-frames-work.html",
        "http://microsoft.com/iframes-actually-work-this-way.html",
    ])


def test_page_parse_baseurl():
    session = NoIOSession()

    page = """
        <html>
            <head>
                <link href="some_css_thing.css"
                    ref="stylesheet" type="text/css">
                <base href="http://other-base-url.net">
            </head>
            <body background="http://image-at-root.com/">
            </body>
        </html>
    """

    base_url, urls = session.scan_page("http://base_url.com/", page)

    assert base_url == "http://other-base-url.net"
    assert set(urls) == set([
        "http://other-base-url.net",
        "some_css_thing.css",
        "http://image-at-root.com/",
    ])
