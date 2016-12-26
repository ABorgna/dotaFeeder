import asyncio
import feedparser
import html
import logging
import os.path
import pickle
import re
from time import sleep

from pprint import pprint

class DotaFeeder:
    DOTA2_BLOG_RSS_URL = "http://blog.dota2.com/feed/"
    STEAM_NEWS_JSON_URL = "http://api.steampowered.com/ISteamNews/GetNewsForApp"\
                          "/v0002/?appid=570&maxlength=300&format=json"
    BELVEDERE_REDDIT_RSS_URL = "https://www.reddit.com/user/SirBelvedere/.rss"

    PICKLE_FILE = "feeder_status.pickle"

    HTML_STRIP_RE = re.compile(r'(<!--.*?-->|<[^>]*>)')

    class Event:
        def __init__(self, type, title, link=None, description=None, time=None):
            self.type = type
            self.title = title
            self.link = link
            self.description = description
            self.time = time

    def __init__(self, polling_interval=30,
                 fetchBlogposts=True,
                 fetchBelvedere=True):
        self.callbacks = []
        self.polling_interval = polling_interval
        self.fetchBlogposts = fetchBlogposts
        self.fetchBelvedere = fetchBelvedere
        self._loadPickle()

    def addListener(self, callback):
        assert(asyncio.iscoroutinefunction(callback))
        self.callbacks.append(callback)

    def start(self):
        logging.info("Pooling updates...")

        if self.fetchBlogposts:
            asyncio.ensure_future(self._runInLoop(self._parseBlog))
        if self.fetchBelvedere:
            asyncio.ensure_future(self._runInLoop(self._parseBelvedere))

    def stop(self):
        self._savePickle()

    def getLastEvent(self, type=None):
        blog = self.pickle["lastBlogpost"]
        belv = self.pickle["lastBelvedere"]

        if type == "blogpost":
            return blog
        elif type == "belvedere":
            return belv
        elif type is None:
            return belv if belv.time >= blog.time else blog
        else:
            return None

    #### Utils

    async def _publish(self, event):
        for c in self.callbacks:
            await c(event)

    def _loadPickle(self):
        if os.path.exists(self.PICKLE_FILE):
            with open(self.PICKLE_FILE,'rb') as h:
                self.pickle = pickle.load(h)
        else:
            self.pickle = {
                    "previousBlogposts": [],
                    "previousBelvedere": [],
                    "lastBlogpost": None,
                    "lastBelvedere": None,
            }

    def _savePickle(self):
        with open(self.PICKLE_FILE,'wb') as h:
            pickle.dump(self.pickle, h)

    def _stripHTML(self,text):
        # Note that this is not a sanitizer
        return self.HTML_STRIP_RE.sub('',text)

    async def _runInLoop(self, fn):
        try:
            while True:
                await fn()
                await asyncio.sleep(self.polling_interval)
        except KeyboardInterrupt:
            self._savePickle()
            raise

    #### Parsers

    async def _parseBlog(self):
        try:
            feed = feedparser.parse(self.DOTA2_BLOG_RSS_URL)
            logging.debug("Blog feed status %s", feed.status)
            if feed.status != 200:
                return False
        except KeyboardInterrupt:
            raise
        except:
            logging.exception("message")
            return False

        firstValid = True
        for entry in feed.entries:
            if entry.id in self.pickle["previousBlogposts"]:
                continue
            self.pickle["previousBlogposts"].append(entry.id)

            logging.info("New blogpost entry, '%s'", entry.title)

            entry.description = self._stripHTML(entry.description)
            entry.description = html.unescape(entry.description)

            event = self.Event("blogpost", entry.title, entry.link,
                               entry.description, entry.updated_parsed)

            if firstValid:
                self.pickle["lastBlogpost"] = event
                firstValid = False

            await self._publish(event)

        self._savePickle()

        return True

    async def _parseBelvedere(self):
        try:
            feed = feedparser.parse(self.BELVEDERE_REDDIT_RSS_URL)
            logging.debug("Belvedere feed status %s", feed.status)
            if feed.status != 200:
                return False
        except KeyboardInterrupt:
            raise
        except:
            logging.exception("message")
            return False

        firstValid = True
        for entry in feed.entries:
            if "/u/SirBelvedere on" in entry.title:
                continue
            if entry.id in self.pickle["previousBelvedere"]:
                continue
            self.pickle["previousBelvedere"].append(entry.id)

            logging.info("New belvedere entry, '%s'", entry.title)

            description = self._stripHTML(entry.summary)[:100]
            description = html.unescape(description) + "…"

            event = self.Event("belvedere", entry.title, entry.link,
                                description, entry.updated_parsed)

            if firstValid:
                self.pickle["lastBelvedere"] = event
                firstValid = False

            await self._publish(event)

        self._savePickle()

        return True

