# DeleteWatch

A Telegram bot that monitors and logs deleted messages in chats, saving them to a SQLite database for later retrieval. The bot also provides admin commands to search and review deleted messages by user ID, view stats, and debug the database.

---

## Features

- Tracks all new messages (text and optionally media) and saves them to a SQLite database.
- Detects when messages are deleted and marks them accordingly.
- Sends notifications to the admin about deleted messages.
- Allows admin to search deleted messages by user ID.
- Provides statistics about deleted messages and tracked chats.
- Debug commands to inspect recent messages in the database.
- Fully configurable via `.env` file.

---

## Requirements

- Python 3.7+
- [Telethon](https://docs.telethon.dev/en/stable/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

## Installation

1. Clone this repository or copy the bot code.

2. Install dependencies:

   ```bash
   pip install telethon python-dotenv
   ```

3. Create a `.env` file in the project directory with the following variables:

   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   ADMIN_ID=your_telegram_user_id
   DB_NAME=deleted_messages.db          # Optional, default is 'deleted_messages.db'
   SESSION_NAME=client_session          # Optional, default is 'client_session'
   LOG_LEVEL=INFO                      # Optional, e.g. DEBUG, INFO, WARNING
   LOG_FILE=                          # Optional, path to log file
   MAX_SEARCH_RESULTS=10               # Optional, max search results for /search command
   MAX_MESSAGE_DISPLAY_LENGTH=100     # Optional, max length of message preview
   NOTIFY_DELETIONS=true              # Optional, notify admin on deletions (true/false)
   SAVE_MEDIA_MESSAGES=true            # Optional, save media messages text placeholder
   ```

4. Get your `API_ID` and `API_HASH` from [https://my.telegram.org](https://my.telegram.org).

5. Get your numeric Telegram user ID (for `ADMIN_ID`) by messaging [@userinfobot](https://t.me/userinfobot).

---

## Usage

Run the bot with:

```bash
python main.py
```

The bot will start monitoring chats and log deleted messages.

---

## Admin Commands

Available only to the configured `ADMIN_ID`:

- `/search user_id`  
  Search for deleted messages from a specific user by their Telegram user ID.

- `/stats`  
  View statistics about deleted messages, tracked users, and chats.

- `/debug`  
  Show recent 10 messages stored in the database for debugging.

- `/help`  
  Show the help message with commands and usage instructions.

---

## Notes

- The bot ignores messages from the admin user and commands (messages starting with `/`).
- Media messages are saved as `[Media/Non-text message]` text placeholder (configurable).
- Notifications for deletions can be toggled via `.env`.
- Database is a local SQLite file (default: `deleted_messages.db`).

---

## Developer

**Pouria Hosseini**  
Telegram: [@isPoori](https://t.me/isPoori)  

---

Feel free to contribute or open issues for improvements and bug fixes.

---

*Thank you for DeleteWatch!*
