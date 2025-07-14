""" rss2discord implementation """

import argparse
import collections
import json
import logging
import re
import typing
import urllib.parse

import atomicwrites
import feedparser
import html_to_markdown
import requests
from bs4 import BeautifulSoup

from . import __version__

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def parse_arguments():
    """ Parse the commandline arguments """
    parser = argparse.ArgumentParser(
        "rss2discord", description="Forward RSS feeds to a Discord webhook")

    parser.add_argument("config", nargs='+', type=str,
                        help="Configuration file, one per webhook")
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help="Do a dry run, don't perform any actions")
    parser.add_argument('--populate', '-p', action='store_true',
                        help="Populate the database without sending new notifications")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output logging level", default=0)
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__.__version__}")

    return parser.parse_args()


FeedConfig = collections.namedtuple(
    'FeedConfig', ['feed_url', 'username', 'avatar_url', 'include_summary', 'include_image'])


def parse_config(config):
    """ Parse a feed config from a configuration dict """
    return FeedConfig(config.get('feed_url'),
                      config.get('username'),
                      config.get('avatar_url'),
                      config.get('include_summary', True),
                      config.get('include_image', True),
                      )


def to_markdown(html):
    """ Convenient wrapper for Discord-friendly Markdown conversion """
    if not html:
        return ''
    return html_to_markdown.convert_to_markdown(
        html,
        heading_style='atx',
        strip_newlines=True,
        escape_misc=False,
        wrap=False,
        bullets='*',
        strip=['img']).strip().replace('\t', '  ')


def get_content(entry):
    """ Get the item content from some feed text; returns the Markdown and
    a list of image attachments """

    # extract the images (content priority)
    if 'content' in entry:
        html = entry.content[0].value
    elif 'summary' in entry:
        html = entry.summary
    else:
        html = ''
    soup = BeautifulSoup(html, features="html.parser")
    images = [urllib.parse.urljoin(entry.link, img['src'])
              for img in soup.find_all('img', src=True)]

    # convert the text (summary priority)
    if 'summary' in entry and entry.summary:
        md_text = to_markdown(entry.summary)
    elif 'content' in entry and entry.content[0].value:
        md_text = to_markdown(entry.content[0].value)
    else:
        md_text = ''

    return md_text, images


class DiscordRSS:
    """ Discord RSS agent """

    def __init__(self, config):
        """ Set up the Discord RSS agent """
        self.webhook = config['webhook']

        defaults = parse_config(config)

        self.feeds = [defaults._replace(feed_url=feed) if isinstance(feed, str)
                      else defaults._replace(**feed)
                      for feed in config['feeds']]
        self.database_file = config.get('database', '')
        self.database = set()

        LOGGER.debug("Initialized RSS agent; feeds=%s database=%s",
                     self.feeds,
                     self.database_file)

    def process(self, options):
        """ Process all of the configured feeds """
        if self.database_file:
            try:
                with open(self.database_file, 'r', encoding='utf-8') as file:
                    self.database = set(
                        line.strip() for line in file.readlines())
            except FileNotFoundError:
                LOGGER.info("Database file %s not found, will create later",
                            self.database_file)

        for feed in self.feeds:
            LOGGER.debug("Processing feed %s", feed.feed_url)
            try:
                self.process_feed(options, feed)
            except Exception as error:  # pylint:disable=broad-exception-caught
                LOGGER.exception(
                    "Got error processing feed %s: %s", feed.feed_url, error)

        if self.database_file and not options.dry_run:
            LOGGER.debug("Writing database %s", self.database_file)
            with atomicwrites.atomic_write(self.database_file, overwrite=True) as file:
                file.write('\n'.join(self.database))

    def process_feed(self, options, feed: FeedConfig):
        """ Process a specific feed """
        data = feedparser.parse(feed.feed_url)

        if data.bozo:
            LOGGER.warning("Got error parsing %s: %s (%d)",
                           feed.feed_url,
                           data.error, data.status)
            return

        for entry in data.entries:
            if entry.id not in self.database:
                LOGGER.info("Found new entry: %s", entry.id)

                try:
                    if options.populate or self.process_entry(options, feed, data.feed, entry):
                        self.database.add(entry.id)
                except Exception as error:  # pylint:disable=broad-exception-caught
                    LOGGER.exception(
                        "Got error processing entry %s: %s", entry.link, error)

    def process_entry(self, options, config, feed, entry):
        """ Process a feed entry """
        payload = {}
        if config.username:
            payload['username'] = config.username
        if config.avatar_url:
            payload['avatar_url'] = config.avatar_url

        md_text, images = get_content(entry)

        text = f'## [{to_markdown(entry.title)}]({entry.link})'
        if config.include_summary:
            text += f'\n{md_text}\n-# [Read more...](<{entry.link}>)'

        embed = {
            'type': 'rich',
            'url': entry.link,
            'author': {
                'url': feed.link,
                'name': to_markdown(feed.title),
            },
            'description': text,
        }

        if config.include_image:
            if 'media_content' in entry:
                for item in entry.media_content:
                    if item['medium'] == 'image':
                        embed['image'] = {
                            'url': item['url'],
                            'height': int(item['height']) if 'height' in item else None,
                            'width': int(item['width']) if 'width' in item else None,
                        }
                    break
            elif images:
                embed['image'] = {'url': images[0]}

        payload['embeds'] = [embed]

        if options.dry_run:
            LOGGER.info("Dry-run; not sending entry: %s", payload)
            return False

        LOGGER.debug("Posting entry: %s", payload)
        request = requests.post(self.webhook,
                                headers={'Content-Type': 'application/json'},
                                json=payload,
                                timeout=30)

        if request.status_code // 100 == 2:
            LOGGER.debug("Success: %d", request.status_code)
            return True

        LOGGER.warning("Got error %d: %s", request.status_code, request.text)
        return False


def main():
    """ Main entry point """
    options = parse_arguments()
    logging.basicConfig(level=LOG_LEVELS[min(
        options.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    for config_file in options.config:
        with open(config_file, 'r', encoding='utf-8') as file:
            config = json.load(file)

        rss = DiscordRSS(config)
        rss.process(options)


if __name__ == "__main__":
    main()
