# Actions and Logs

## Bulk Actions

The UI exposes the original CLI action set:

- Like
- Retweet
- Follow
- Reply
- AI reply
- Bookmark
- View
- Protect
- Unprotect
- Follow boost
- Boost
- Fix usernames
- Purge

## Dry Run

Dry run is enabled by default for the Actions page. When enabled, the app reports what would run without performing the real action.

This reduces accidental destructive or high-volume actions.

## Live Action Console

Long actions run through `ui_live.py action`. The renderer appends each streamed output line to the Action Console.

This solved the earlier issue where the user only saw results after the whole process finished.

## Operation Logs

The Python core writes operation logs to:

```text
tweet_log.json
```

The Logs page reads recent entries and shows:

- timestamp
- username
- action
- success state
- target or error detail

## Retry Behavior

The Python core includes retry support for tweet/post operations. Retry count and timeout behavior remain in `tweeter.py`.

## Error Visibility

The UI now makes failures visible in several places:

- row status pills
- live consoles
- toast messages
- logs page
- check result rows

