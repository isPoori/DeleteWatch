import sqlite3
import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events

# Load environment variables
load_dotenv()

# Configuration from .env file
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Optional configurations with defaults
DB_NAME = os.getenv('DB_NAME', 'deleted_messages.db')
SESSION_NAME = os.getenv('SESSION_NAME', 'client_session')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE')
MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', '10'))
MAX_MESSAGE_DISPLAY_LENGTH = int(os.getenv('MAX_MESSAGE_DISPLAY_LENGTH', '100'))
NOTIFY_DELETIONS = os.getenv('NOTIFY_DELETIONS', 'true').lower() == 'true'
SAVE_MEDIA_MESSAGES = os.getenv('SAVE_MEDIA_MESSAGES', 'true').lower() == 'true'

class DeletedMessagesClient:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                chat_id INTEGER,
                chat_title TEXT,
                message_text TEXT,
                message_date TEXT,
                deleted_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_message(self, message):
        """Save message to database for potential deletion tracking"""
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Get user info
            user = message.sender
            username = getattr(user, 'username', None)
            first_name = getattr(user, 'first_name', None)
            last_name = getattr(user, 'last_name', None)
            
            # Get chat info
            chat = message.chat
            chat_title = getattr(chat, 'title', None)
            
            cursor.execute('''
                INSERT OR REPLACE INTO deleted_messages 
                (message_id, user_id, username, first_name, last_name, 
                 chat_id, chat_title, message_text, message_date, deleted_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.id,
                user.id if user else None,
                username,
                first_name,
                last_name,
                message.chat_id,
                chat_title,
                message.text or ('[Media/Non-text message]' if SAVE_MEDIA_MESSAGES else None),
                message.date.isoformat() if message.date else None,
                None  
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving message: {e}")
    
    def mark_as_deleted(self, message_ids, chat_id):
        """Mark messages as deleted in database"""
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            deleted_time = datetime.now().isoformat()
            
            for msg_id in message_ids:
                cursor.execute('''
                    UPDATE deleted_messages 
                    SET deleted_date = ? 
                    WHERE message_id = ? AND chat_id = ? AND deleted_date IS NULL
                ''', (deleted_time, msg_id, chat_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error marking messages as deleted: {e}")
    
    def get_deleted_by_user(self, user_id):
        """Get all deleted messages from a specific user"""
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message_id, username, first_name, last_name, 
                       chat_title, message_text, message_date, deleted_date
                FROM deleted_messages 
                WHERE user_id = ? AND deleted_date IS NOT NULL
                ORDER BY deleted_date DESC
            ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return results
            
        except Exception as e:
            logging.error(f"Error retrieving deleted messages: {e}")
            return []
    
    async def start_client(self):
        """Start the Telegram client"""
        await self.client.start()
        
        # Message handler
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            try:
                if event.sender_id == ADMIN_ID:
                    return
                    
                if event.text and event.text.startswith('/'):
                    return
                
                sender_info = "Unknown"
                if event.sender:
                    sender_info = f"{event.sender.id} ({getattr(event.sender, 'first_name', 'No name')})"
                
                chat_info = f"Chat ID: {event.chat_id}"
                if event.chat:
                    chat_title = getattr(event.chat, 'title', 'Private Chat')
                    chat_info = f"Chat: {chat_title} (ID: {event.chat_id})"
                
                print(f"📨 New message from {sender_info} in {chat_info}: {event.text[:50] if event.text else '[Media]'}...")
                
                self.save_message(event.message)
                
            except Exception as e:
                print(f"Error in message handler: {e}")
        
        # Deleted message handler
        @self.client.on(events.MessageDeleted)
        async def deletion_handler(event):
            try:
                print(f"🗑️ Deletion event detected!")
                
                # Get deleted IDs
                deleted_ids = []
                
                if hasattr(event, 'deleted_ids') and event.deleted_ids:
                    deleted_ids = event.deleted_ids
                elif hasattr(event, 'deleted_id') and event.deleted_id:
                    deleted_ids = [event.deleted_id]
                
                print(f"Deleted IDs: {deleted_ids}")
                
                chat_id = getattr(event, 'chat_id', None)
                
                if not chat_id and hasattr(event, 'chat') and event.chat:
                    chat_id = event.chat.id
                
                if not chat_id and hasattr(event, 'input_chat') and event.input_chat:
                    try:
                        chat_id = event.input_chat.chat_id
                    except:
                        pass
                
                print(f"Chat ID from event: {chat_id}")
                
                if deleted_ids:
                    if not chat_id:
                        print("No chat_id in event, searching database...")
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        for msg_id in deleted_ids:
                            cursor.execute('SELECT chat_id, user_id, first_name FROM deleted_messages WHERE message_id = ?', (msg_id,))
                            result = cursor.fetchone()
                            if result:
                                chat_id = result[0]
                                print(f"Found in database: chat_id {chat_id} for message {msg_id} from user {result[1]} ({result[2]})")
                                break
                        
                        conn.close()
                    
                    if chat_id:
                        print(f"✅ Marking {len(deleted_ids)} messages as deleted in chat {chat_id}")
                        self.mark_as_deleted(deleted_ids, chat_id)
                        
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        deleted_info = []
                        for msg_id in deleted_ids:
                            cursor.execute('''
                                SELECT user_id, first_name, username, message_text 
                                FROM deleted_messages 
                                WHERE message_id = ? AND chat_id = ? AND deleted_date IS NOT NULL
                            ''', (msg_id, chat_id))
                            result = cursor.fetchone()
                            if result:
                                user_id, first_name, username, text = result
                                deleted_info.append({
                                    'user_id': user_id,
                                    'name': first_name or 'Unknown',
                                    'username': username,
                                    'text': text[:50] + '...' if text and len(text) > 50 else text or '[Media]'
                                })
                        
                        conn.close()
                        
                        # Notify admin about deletions if enabled
                        if NOTIFY_DELETIONS:
                            try:
                                notification = f"🗑️ **{len(deleted_ids)} message(s) deleted in chat {chat_id}**\n\n"
                                
                                for i, info in enumerate(deleted_info[:5], 1):
                                    user_display = f"{info['name']}"
                                    if info['username']:
                                        user_display += f" (@{info['username']})"
                                    user_display += f" (ID: {info['user_id']})"
                                    
                                    notification += f"**{i}.** {user_display}\n"
                                    notification += f"💬 `{info['text']}`\n\n"
                                
                                if len(deleted_info) > 5:
                                    notification += f"... and {len(deleted_info) - 5} more messages"
                                
                                await self.client.send_message(ADMIN_ID, notification)
                                print("✅ Deletion notification sent to admin")
                                
                            except Exception as e:
                                print(f"❌ Failed to send deletion notification: {e}")
                    else:
                        print("❌ Could not determine chat_id for deleted messages")
                        print("Attempting to mark messages as deleted without chat_id...")
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        deleted_time = datetime.now().isoformat()
                        
                        for msg_id in deleted_ids:
                            cursor.execute('''
                                UPDATE deleted_messages 
                                SET deleted_date = ? 
                                WHERE message_id = ? AND deleted_date IS NULL
                            ''', (deleted_time, msg_id))
                            
                            if cursor.rowcount > 0:
                                print(f"✅ Marked message {msg_id} as deleted (without chat_id)")
                        
                        conn.commit()
                        conn.close()
                else:
                    print("❌ No deleted IDs in the event")
                    
            except Exception as e:
                print(f"❌ Error in deletion handler: {e}")
                import traceback
                traceback.print_exc()
        
        # Admin commands
        @self.client.on(events.NewMessage(chats=ADMIN_ID, pattern=r'/search (\d+)'))
        async def search_with_id_command(event):
            user_id = int(event.pattern_match.group(1))
            deleted_messages = self.get_deleted_by_user(user_id)
            
            if not deleted_messages:
                await event.respond(f"❌ No deleted messages found for user ID: {user_id}")
                return
            
            response = f"🗑️ **Deleted Messages for User ID: {user_id}**\n\n"
            
            for i, msg in enumerate(deleted_messages[:MAX_SEARCH_RESULTS], 1):
                msg_id, username, first_name, last_name, chat_title, text, msg_date, del_date = msg
                
                user_name = []
                if first_name:
                    user_name.append(first_name)
                if last_name:
                    user_name.append(last_name)
                if username:
                    user_name.append(f"(@{username})")
                
                name = " ".join(user_name) if user_name else "Unknown User"
                
                display_text = text[:MAX_MESSAGE_DISPLAY_LENGTH] + "..." if len(text) > MAX_MESSAGE_DISPLAY_LENGTH else text
                
                response += f"**{i}.** {name}\n"
                response += f"📍 Chat: {chat_title or 'Private'}\n"
                response += f"💬 Message: `{display_text}`\n"
                response += f"🕐 Sent: {msg_date[:16] if msg_date else 'Unknown'}\n"
                response += f"🗑️ Deleted: {del_date[:16] if del_date else 'Unknown'}\n\n"
            
            if len(deleted_messages) > MAX_SEARCH_RESULTS:
                response += f"... and {len(deleted_messages) - MAX_SEARCH_RESULTS} more messages"
            
            await event.respond(response)
        
        @self.client.on(events.NewMessage(chats=ADMIN_ID, pattern='/search'))
        async def search_command(event):
            if event.text.strip() == '/search':
                await event.respond(
                    "Please provide a user ID to search for.\n\n"
                    "**Usage:** `/search <user_id>`\n"
                    "**Example:** `/search 123456789`"
                )
        
        @self.client.on(events.NewMessage(chats=ADMIN_ID, pattern='/stats'))
        async def stats_command(event):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM deleted_messages WHERE deleted_date IS NOT NULL")
            deleted_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM deleted_messages WHERE deleted_date IS NOT NULL")
            unique_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM deleted_messages WHERE deleted_date IS NULL")
            active_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT chat_id) FROM deleted_messages")
            unique_chats = cursor.fetchone()[0]
            
            conn.close()
            
            await event.respond(
                f"📊 **Database Statistics**\n\n"
                f"🗑️ Deleted messages: {deleted_count}\n"
                f"👥 Users with deletions: {unique_users}\n"
                f"💬 Active messages tracked: {active_messages}\n"
                f"🏠 Unique chats: {unique_chats}\n"
            )
        
        @self.client.on(events.NewMessage(chats=ADMIN_ID, pattern='/debug'))
        async def debug_command(event):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message_id, user_id, username, first_name, chat_id, 
                       message_text, message_date, deleted_date
                FROM deleted_messages 
                ORDER BY id DESC 
                LIMIT 10
            ''')
            
            recent_messages = cursor.fetchall()
            conn.close()
            
            if not recent_messages:
                await event.respond("🔍 **Debug Info**\n\nNo messages found in database.")
                return
            
            response = "🔍 **Debug Info - Recent 10 Messages:**\n\n"
            
            for i, msg in enumerate(recent_messages, 1):
                msg_id, user_id, username, first_name, chat_id, text, msg_date, del_date = msg
                status = "🗑️ DELETED" if del_date else "✅ ACTIVE"
                
                response += f"**{i}.** ID: {msg_id} | User: {user_id}\n"
                response += f"Name: {first_name or 'Unknown'} (@{username or 'no_username'})\n"
                response += f"Chat: {chat_id} | Status: {status}\n"
                response += f"Text: {(text or 'No text')[:30]}...\n\n"
            
            await event.respond(response)
        
        @self.client.on(events.NewMessage(chats=ADMIN_ID, pattern='/help'))
        async def help_command(event):
            await event.respond(
                "🤖 **@OmgaDeveloper Deleted Messages Monitor - Help**\n\n"
                "**Available Commands:**\n"
                "`/search user_id` - Search deleted messages by user ID\n"
                "`/stats` - View database statistics\n"
                "`/debug` - Show recent messages in database\n"
                "`/help` - Show this help message\n\n"
                "**How to get User ID:**\n"
                "1. Forward a message from the user to @userinfobot\n"
                "2. @userinfobot will reply with their user ID\n\n"
                "**Example Usage:**\n"
                "`/search 123456789` - Shows deleted messages from user 123456789\n\n"
                "Developer : @isPoori | Github : https://github.com/isPoori"
            )
        
        print("Client started successfully!")
        print("The client is now monitoring for deleted messages...")
        print("You can now use /help to see available commands")
        
        await self.client.run_until_disconnected()

def main():
    """Main function"""
    log_config = {
        'level': getattr(logging, LOG_LEVEL.upper()),
        'format': '%(asctime)s - %(levelname)s - %(message)s'
    }
    
    if LOG_FILE:
        log_config['filename'] = LOG_FILE
    
    logging.basicConfig(**log_config)
    
    if not API_ID or not API_HASH:
        print("Please configure API_ID and API_HASH in .env file")
        print("Get them from https://my.telegram.org")
        return
    
    if not ADMIN_ID or ADMIN_ID == 0:
        print("Please configure ADMIN_ID in .env file")
        print("Get your numeric user ID from @userinfobot")
        return
    
    # Start
    client = DeletedMessagesClient()
    
    try:
        asyncio.run(client.start_client())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()