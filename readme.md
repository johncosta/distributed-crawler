Crawler demo project
====================

A little(-ish) thingy to show off what I can do (when overengineering things
at midnight). This was made with a tight deadline, relative to the level I
built it at, so I punted a lot of things.

Usage:
------

- with docker:
    1. run ./build.sh (or cat it and run each command individually)
    2. run `docker run -ti -P --rm --name central lahwran/crawler-coord`. the
        important parts there are `--name central` and `lahwran/crawler-coord`;
        you can background it if you're into such things. (I'm not.) Note that
        it's a huge pain to talk to docker instances from your mac if using
        boot2docker, which is why `lahwran/crawler-curl` exists.
    3. run as many of `docker run -ti --rm --link central:coord lahwran/crawler-drone`
        as you want drones. the important parts there are `--link central:coord`
        - don't change `coord` - and `lahwran/crawler-drone`. the coordination
        node will dictate parallelism per drone, and defaults to two requests
        in flight at once on each drone. (add --help to your invocation of
        either -coord or -drone to get more information.)
    4. if necessary, run something like `docker run -ti --rm --link central:coord lahwran/crawler-curl curl -X POST --data-binary @- http://coord:8080/`.
        this will allow you to control the central api even if your mac vm won't
        map it correctly.
    5. yay, images!
- without docker is also possible, install requirements.txt with pip and then
    look at `python -m crawler.main --help`.

Known issues
------------

- Sometimes you get a TLS error from the drone. I decided it wasn't worth the
    time for a demo project to figure out why, especially considering how much
    I overdid the rest of it and how much time that took.
- I was originally going to try to do unicode support, but I slipped up
    in at least one place, and it started looking like it'd take too much time
    to fix that, so I just tore out all the b markers and the unicode_literal
    future import and left it python 2 style.
    

API
---

###### `POST /`

send a newline-separated list of urls, not specially encoded (sorry, these
seed urls can't have newlines). Returns a json-encoded job id.

###### `GET /status/<job-id>`

returns some json information about the job. looks like:

    {
        "result_count": 131,
        "crawled_urls": {
            "finished": 169,
            "in_progress": 7,
            "waiting_in_queue": 0}
        }
    }

###### `GET /status/all`

Return statuses for all running jobs. `{job id: job status as above}`.


###### `GET /results/<job-id>`

Return a json list of image urls that have been discovered by this job.


Notes
-----

The goal here was to create a crawler to find images, that can parallelize
by running multiple instances of it in docker. Here are some thoughts I had
along the way:

- Images or urls from image tags or image-like urls: I considered three
    different ways to determine if a url was an image; I ended up deciding
    on the simplest and most error prone, matching a regex against the url's
    path, but I also thought about calling HEAD on each url and checking the
    mimetype. As that would be effectively another level deep of spidering,
    I decided against it. I also considered filtering based on what urls were
    found in image tags, but many urls that are images are also found in links,
    so I decided against that as well, as it would leave some out. I considered
    a hybrid that had different levels of confidence, but that seemed like
    overcomplication for a demo project.
- Cerealization: I considered Cap'n proto initially, but I hadn't actually used
    that before, so I decided to stick with what I had done before. However,
    I was a bit embarrassed about my habit of using json-on-a-line protocols,
    so I tried to just do line-command based; that didn't work out too well,
    as it turned out that urls have newlines in them in the wild! So I added
    json back in to escape the urls in transit.
- Architecture: I initially wanted to use an entirely peer to peer queue
    system, but such a thing would be Very Hard(tm) to make, and since I
    didn't find it anywhere already in existence, I decided to skip it. ZeroMQ
    seemed to come pretty close, but it wasn't quite a task queue, as far as I
    could tell. However, I did get someone on irc thinking I was crazy for
    even asking, so maybe that's an indication I misunderstood so badly that
    they didn't even bother to explain.
- Code reuse: I wrote this entirely in twisted, and as such decided to use a
    fair number of little chunks of code I'd written to make the way I do
    things in twisted a bit nicer. I marked them sufficiently to be clear they
    were not written for this project; it still holds up as a demo project
    done in a short period of time.
- Use of docker: I'm still not sure I got it quite right in terms of using
    docker idiomatically, but I think I got pretty close, if I didn't nail it.
    This was my first time using docker in anything, and it was fairly
    confusing to rush through at high velocity - what would normally have been
    minor bumps were compressed together into a small timespan, and felt much
    bigger.
- Use of external systems: Because docker was used for this, I could have used
    pre-prepared external services (say, postgres, redis, mongodb, blah blah).
    I am not generally a fan of small projects using big databases like that,
    because in my experience they typically take a good deal of spinup time.
    In the spirit of "use boring technology", I try to use what I know, rather
    than jumping into new things just-because, which is a thing to do when not
    in "get it done now" mode. (yay personal projects!)

    I also didn't want to add overhead for communication, and since I didn't
    have a good handle on the performance characteristics of the databases I'd
    used less and definitely did not want to use the one database I do
    understand reasonably well (postgres), I chose to write my own protocol
    that I was fully in control of.
- Saving: because I didn't use an existing database, saving didn't come for
    free. I decided to not include any automatic saving of the results, leaving
    it as a crawling system that is focused on its responsibilities and lets
    some other client save the results when it's ready to do so.
- Performance: While I designed this using habits I have to increase
    performance in the little things - multiple requests in flight at once,
    an http library that supports connection pooling, keeping live connections
    between the drones and central, etc - there are probably large-scale ways
    that it could be much faster. For instance, it won't run in pypy, because
    used LXML. Or similarly, I suspect I could probably optimize the xpath
    that I'm using - I'm not familiar with the xpath execution thingy, but it
    seems reasonable to worry that it might be O(n*m), where n is the number of
    nodes and m is the number of tags I'm searching for.
- Robots.txt parsing: I considered doing robots.txt parsing and filtering urls
    by it, but ended up deciding that figuring out how to provide the funky
    parameters that the recent robots parsing library wanted would be too
    much effort for the time I had. It'd be a cool next feature, though.
    The library I looked at was https://github.com/seomoz/reppy.
