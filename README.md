# rss2discord

A simple script for posting RSS feeds to a Discord webhook

The configuration format is a JSON file with the following format:

```json
{
    "webhook": "https://discord.com/api/webhooks/<channel_id>/<token>",
    "database": "feed.db",
    "username": "RSS Bot",
    "avatar_url": "https://example.com/bot.png",
    "include_summary": true,

    "feeds": [{
        "feed_url": "https://example.com/feed",
        "username": "Example Feed",
        "avatar_url": "https://example.com/image.png"
    }, {
        "feed_url": "https://example.com/another_feed",
        "avatar_url": "https://example.com/another_image.png",
        "include_summary": false
    }]
}
```

At the top level, only the `webhook` field is required, and for each feed, only `feed_url` is required. If you only care about providing a feed URL, you can provide it as a string instead of a dictionary (and it will use the values provided at the top level, if any).

See the [Discord Intro to Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for information about setting up a webhook.
