import feedparser
import html
import logging
import os.path
import pickle
import pprint
import re
from time import sleep

class DotaFeeder:
    DOTA2_BLOG_RSS_URL = "http://blog.dota2.com/feed/"
    STEAM_NEWS_JSON_URL = "http://api.steampowered.com/ISteamNews/GetNewsForApp"\
                          "/v0002/?appid=570&maxlength=300&format=json"
    BELVEDERE_REDDIT_RSS_URL = "https://www.reddit.com/user/SirBelvedere/.rss"

    PICKLE_FILE = "feeder_status.pickle"

    HTML_STRIP_RE = re.compile(r'(<!--.*?-->|<[^>]*>)')

    def __init__(self, polling_interval=30,
                 fetchBlogposts=True,
                 fetchBelvedere=True):
        self.callbacks = []
        self.polling_interval = polling_interval
        self.fetchBlogposts = fetchBlogposts
        self.fetchBelvedere = fetchBelvedere
        self._loadPickle()

    def addListener(self, callback):
        assert(callable(callback))
        self.callbacks.append(callback)

    def run(self):
        try:
            while True:
                if self.fetchBlogposts:
                    self._parseBlog()
                if self.fetchBelvedere:
                    self._parseBelvedere()
                sleep(self.polling_interval)
        except KeyboardInterrupt:
            self._savePickle()
            raise

    #### Utils

    def _publish(self, eventType, link, title, content=None):
        ev = {
            "type": eventType,
            "link": link,
            "title": title,
            "content": content
        }
        for c in self.callbacks:
            try:
                c(ev)
            except:
                logging.exception("message")

    def _loadPickle(self):
        if os.path.exists(self.PICKLE_FILE):
            with open(self.PICKLE_FILE,'rb') as h:
                self.pickle = pickle.load(h)
        else:
            self.pickle = {
                    "previousBlogposts": [],
                    "previousBelvedere": [],
            }

    def _savePickle(self):
        with open(self.PICKLE_FILE,'wb') as h:
            pickle.dump(self.pickle, h)

    def _stripHTML(self,text):
        # Note that this is not a sanitizer
        return self.HTML_STRIP_RE.sub('',text)

    #### Parsers

    def _parseBlog(self):
        try:
            feed = feedparser.parse(self.DOTA2_BLOG_RSS_URL)
            logging.info("Blog feed status %s", feed.status)
            if feed.status != 200:
                return False
        except:
            logging.exception("message")
            return False

        for entry in feed.entries:
            if entry.id in self.pickle["previousBlogposts"]:
                continue
            self.pickle["previousBlogposts"].append(entry.id)

            logging.info("New blogpost entry, '%s'", entry.title)

            entry.description = self._stripHTML(entry.description)
            entry.description = html.unescape(entry.description)
            self._publish("blogpost", entry.link, entry.title, entry.description)
        self._savePickle()

        return True

    def _parseBelvedere(self):
        try:
            feed = feedparser.parse(self.BELVEDERE_REDDIT_RSS_URL)
            logging.info("Belvedere feed status %s", feed.status)
            if feed.status == 200:
                content = feed["items"][0]["summary"]
                content = content[1:100]
            else:
                return False
        except:
            logging.exception("message")
            return False

        for entry in feed.entries:
            if "/u/SirBelvedere on" in entry.title:
                continue
            if entry.id in self.pickle["previousBelvedere"]:
                continue
            self.pickle["previousBelvedere"].append(entry.id)

            logging.info("New belvedere entry, '%s'", entry.title)

            description = self._stripHTML(entry.summary)[:100]
            description = html.unescape(description) + "…"
            self._publish("belvedere", entry.link, entry.title, description)
        self._savePickle()

        return True

