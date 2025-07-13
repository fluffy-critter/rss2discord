# rss2discord

A simple script for posting RSS feeds to a Discord webhook.

## Installation

You can install this using `pipx` or the like, e.g.

```
pipx install rss2discord
```

## Configuration

First, set up a webhook on Discord; consult the [Discord Intro to Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for more information.

Then, for each webhook, create a `.json` file with the following format:

```json
{
    "webhook": "https://discord.com/api/webhooks/<channel_id>/<token>",
    "database": "feed.db",

    "username": "RSS Bot",
    "avatar_url": "https://example.com/bot.png",
    "include_summary": true,
    "include_image": false,

    "feeds": [{
        "feed_url": "https://example.com/feed",
        "username": "Example Feed",
        "avatar_url": "https://example.com/image.png",
        "include_image": true
    }, {
        "feed_url": "https://example.com/another_feed",
        "avatar_url": "https://example.com/another_image.png",
        "include_summary": false
    },
    "https://example.com/feed3",
    "https://example.com/feed4"
    ]
}
```

The schema is pretty basic; at the top level, the following keys are supported:

* `webhook`: the webhook URL (i.e. the channel to post to)
* `database`: The path to the file to store the information about already-seen entries
* `username`: The display name to use for the posting bot (will default to the webhook name)
* `avatar_url`: An image to use as the post avatar (will default to the webhook's icon)
* `include_summary`: Whether to put the feed's summary text into the preview (defaults to `true`)
* `include_image`: Whether to include the primary entry image into the preview (defaults to `true`)

* `feeds`: A list of feeds to send to the channel. A feed can be just a URL, or it can be a configuration blob with the following values:
    * `feed_url`: The URL to the feed
    * `username`, `avatar_url`, `include_summary`, `include_image`: Overrides the top-level configuration

Only `webhook` is required, but `database` is *strongly* recommended.

## Running it

You can run `rss2discord config.json` and it will go ahead and post all new items to the Discord channel. `rss2discord --help` will give you more detailed information about how to use it.

When first setting things up, I highly recommend doing:

```
rss2discord config.json -nvv
```

to get an idea of what will happen, and

```
rss2discord config.json -p
```

to pre-populate the database with existing items so that it doesn't spam the channel, unless you like that sort of thing.

