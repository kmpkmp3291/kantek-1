"""File containing the settings for kantek."""
import os
from typing import Union

api_id: Union[str, int] = ''11539587
api_hash: str = ''7e243ca4dbf28af17e7239a0447cc6b1
phone: str = ''+94 71 149 9331
session_name: str = f'sessions/{os.environ.get("KANTEK_SESSION", "kantek-session")}'

log_bot_token: str = ''5219276096:AAGDyu4x9d9-Al03AdQ7-UTxI6Yli_JU_Mg
log_channel_id: Union[str, int] = ''-430252153

# This is regex so make sure to escape the usual characters
cmd_prefix: str = r'\.'
from telethon import events
from telethon.events import NewMessage

from config import cmd_prefix
from utils.pluginmgr import KantekPlugin


class Ping(KantekPlugin):
    """A short help message for the entire plugin"""
    name = 'Ping'

    @events.register(NewMessage(outgoing=True, pattern=f'{cmd_prefix}ping'))
    async def ping(event):
        """A long message about the command"""
        await event.reply('Pong 🏓')
