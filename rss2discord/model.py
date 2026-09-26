""" Database model """

import datetime
import json
import logging
import typing

LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = 1


class Database:
    """ an rss2discord update log """

    def __init__(self, path):
        self.path = path

        self.feeds: typing.Dict[str, dict] = {}
        self.loose: typing.Dict[str, dict] = {}

    def load(self):
        """ Load the data from the backing store """
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                self._deserialize(file.read())
        except FileNotFoundError:
            LOGGER.info("Database file %s not found, will create later",
                        self.path)

    def _deserialize(self, text: str):
        """ Load the database from the given text string """
        try:
            data = json.loads(text)

            version = data.get('$version', 0)
            if version < SCHEMA_VERSION:
                LOGGER.info("Migrating database %s from version %d to %d",
                            self.path, version, SCHEMA_VERSION)

            if version < 1:
                data = {'loose': data, 'feeds': {}}
                version = 1

            self.feeds = data['feeds']
            self.loose = data.get('loose', {})

        except json.JSONDecodeError:
            LOGGER.info(
                "Database file %s is in pre-JSON format; migrating", self.path)
            self.loose = {
                line.strip(): {
                    'sent': True
                }
                for line in data.splitlines()
            }

    def purge(self, max_age: int) -> int:
        """ Remove items which are more than max_age days old """
        count = 0
        cutoff = (datetime.datetime.now() -
                  datetime.timedelta(days=max_age)).timestamp()

        def do_purge(entries) -> int:
            removes: typing.List[str] = []
            for key, val in entries.items():
                if not 'last_seen' in val or val['last_seen'] < cutoff:
                    removes.append(key)
            for key in removes:
                entries.pop(key)
            return len(removes)

        for feed in self.feeds.values():
            count += do_purge(feed['entries'])
        count += do_purge(self.loose)

        LOGGER.info("%s: Removed %d stale items", self.path, count)
        return count

    def save(self):
        """ serialize the backing store """
        data = {
            '$version': SCHEMA_VERSION,
            'feeds': self.feeds
        }
        if self.loose:
            data['loose'] = self.loose
        with open(self.path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=3)

    def get_feed(self, name: str) -> dict:
        """ get the database entry for the given feed """
        if name not in self.feeds:
            self.feeds[name] = {
                'entries': {},
            }
        return self.feeds[name]

    def get_item(self, feed: dict, guid: str) -> dict:
        """ get a feed item for the given feed """
        if guid in feed['entries']:
            pass
        elif guid in self.loose:
            feed['entries'][guid] = self.loose.pop(guid)
        else:
            feed['entries'][guid] = {}

        return feed['entries'][guid]
