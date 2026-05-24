# UI and UX Work

## Navigation

The desktop app is organized into six main pages:

- Compose
- Actions
- Check
- Accounts
- Settings
- Logs

The sidebar keeps the product surface stable and avoids hiding important workflows behind CLI commands.

## Compose

Compose supports two AI modes:

- Rewrite one base tweet per account.
- Write unique tweets from an instruction.

The user can:

- Select accounts.
- Select a group.
- Attach up to four images.
- Generate AI preview rows.
- Edit each generated text before sending.
- Enable or disable rows.
- Publish selected rows.

Publishing now has live output. Each row has a status:

- Ready
- Queued
- Posting
- Sent
- Error
- Skipped

The Publish Output console shows what is happening while the operation is running.

## Actions

Actions exposes the CLI action surface in the UI:

- Like tweet
- Retweet
- Follow user
- Reply
- AI reply from instruction
- Bookmark
- View
- Protect accounts
- Unprotect accounts
- Follow boost
- Boost mode
- Fix usernames
- Purge dead accounts

The page includes account selection, group selection, dry-run mode and a live console.

## Check

The Check page lets the user verify selected accounts and watch results live. It includes:

- Worker count.
- Deep write test toggle.
- Select all.
- Clear.
- Select failed.
- Delete failed.
- Run check.

Rows update as output arrives, so the user no longer waits until the whole operation finishes.

## Accounts

The Accounts page was reorganized to avoid clipped panels and cramped controls. It includes:

- Manual add account form.
- Bulk Account Import panel.
- Import result summary.
- Group creation.
- Assign selected to group.
- Delete selected.
- Account inventory table.

Bulk import accepts:

```text
username:password:phone:auth_token:ct0
username:password:email:email_password:2fa:ct0:auth_token
```

## Settings

Settings contains:

- AI provider selection.
- Base URL.
- Model.
- Timeout.
- API key.
- OAuth proxy start/stop controls.
- Runtime path preview.
- Proxy list editor.

## Visual Direction

The UI uses a restrained desktop-dashboard style:

- Compact panels.
- Stable table dimensions.
- Status pills.
- Monospace consoles for live output.
- Responsive single-column fallback.
- No marketing-style landing page.

