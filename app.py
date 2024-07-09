import configparser
import json
import asyncio
import re
from datetime import datetime
import os

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel, MessageMediaPhoto

# Function to parse datetime objects in JSON serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        return json.JSONEncoder.default(self, o)

# Function to remove links from the message text
def remove_links(text):
    url_pattern = re.compile(r'https?://\S+|www\.\S+')
    return url_pattern.sub(r'', text)

async def main(api_id, api_hash, phone, username):
    # Create the client and connect
    client = TelegramClient(username, api_id, api_hash)
    await client.start()
    
    # Ensure you're authorized
    if await client.is_user_authorized() == False:
        try:
            await client.send_code_request(phone)
            print("Code sent successfully. Waiting for user input.")
            
            try:
                await client.sign_in(phone, input('Enter the code: '))
            except SessionPasswordNeededError:
                await client.sign_in(password=input('Password: '))
            
            print("Successfully signed in.")
        
        except Exception as e:
            print(f"Failed to send code request: {e}")
            return
    
    # Get the provider channel entity
    provider_channel_input = config['Telegram']['provider_channel_entity']

    try:
        # Attempt to parse as integer (channel ID)
        provider_entity = PeerChannel(int(provider_channel_input))
    except ValueError:
        # If not an integer, treat it as a username or URL
        provider_entity = provider_channel_input

    provider_channel = await client.get_entity(provider_entity)

    # Function to send a message to your channel
    async def send_message_to_my_channel(message_text, photo=None):
        try:
            # Read my channel ID from config
            my_channel_id = config['Telegram']['my_channel_id']
            
            # Fetch entity ID for your channel using its username
            my_channel_entity = await client.get_entity(my_channel_id)
            
            # Remove links from the message text
            clean_message_text = remove_links(message_text)
            
            # Send message with photo if available
            if photo:
                await client.send_file(my_channel_entity, photo, caption=clean_message_text)
            else:
                await client.send_message(my_channel_entity, clean_message_text)
            print("Message sent to my channel successfully.")
        except Exception as e:
            print(f"Failed to send message to my channel: {e}")

    # Event handler for new messages from the provider channel
    @client.on(events.NewMessage(chats=provider_channel))
    async def handle_new_message(event):
        message = event.message
        print(f"New message received from provider channel: {message.text}")
        
        # Check if message has media and if it's a photo
        if message.media and isinstance(message.media, MessageMediaPhoto):
            print("Message contains a photo!")
            # Access photo details
            photo = message.media.photo
            print(f"Photo ID: {photo.id}, Date: {photo.date}")

            # Download the photo
            photo_path = await client.download_media(message.media)
            print(f"Photo downloaded to: {photo_path}")

            # Send the message and photo to your channel
            await send_message_to_my_channel(message.text, photo_path)

            # Optionally, delete the photo after sending it
            os.remove(photo_path)
        else:
            # Send the message (without photo) to your channel
            await send_message_to_my_channel(message.text)

    print(f"Listening for new messages in provider channel: {provider_channel_input}...")
    
    # Run event loop
    await client.run_until_disconnected()

# Read configuration from file
config = configparser.ConfigParser()
config.read("config.ini")

# Retrieve configuration values
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
phone = config['Telegram']['phone']
username = config['Telegram']['username']

asyncio.run(main(api_id, api_hash, phone, username))