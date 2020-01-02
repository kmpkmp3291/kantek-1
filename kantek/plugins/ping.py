from telethon import events
from telethon.events import NewMessage

from config import cmd_prefix
from utils.pluginmgr import KantekPlugin


class Ping(KantekPlugin):
    name = 'Ping'
    help = 'Some help message'

    @events.register(NewMessage(outgoing=True, pattern=f'{cmd_prefix}ping'))
    async def ping(event):
        """Play ping pong 🏓"""
        await event.reply('Pong 🏓')
