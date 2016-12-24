import asyncio
import discord
import logging
from pprint import pprint

class DiscordBot:

    def __init__(self, token, feeder):
        self.token = token

        self.feeder = feeder
        self.feeder.addListener(self.updateListener)

        self.client = discord.Client()
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.pendingUpdates = []
        self.lastMsgAuthor = {} # per channel

    async def run(self):
        while True:
            try:
                await self.client.start(self.token)
            except KeyboardInterrupt:
                raise
            except:
                logging.exception("message")
                logging.info("DiscordBot crashed, restarting in a minute")
                await asyncio.sleep(60)

    async def stop(self):
        if self.client.is_logged_in:
            await self.client.logout()

    async def on_ready(self):
        logging.info('Logged in as %s - %s', self.client.user.name, self.client.user.id)

        self.pendingUpdates.sort(key=lambda x: x.time)
        for e in self.pendingUpdates:
            await self.updateListener(e)
        self.pendingUpdates = []

    async def on_message(self, msg):
        logging.info('Message from %s@%s: %s', msg.author, msg.channel, msg.content)
        self.lastMsgAuthor[msg.channel] = msg.author

    async def updateListener(self, event):
        if not self.client.is_logged_in:
            logging.info('Queuing update until discord is logged')
            self.pendingUpdates.append(event)
            return

        msg = "A new update is here!\n" \
              + event.title + "\n" \
              + event.link + "\n" \
              + "\n" \
              + event.description + "\n"
        for s in self.client.servers:
            if self.lastMsgAuthor.get(s.default_channel, None) == self.client.user:
                await self.client.send_message(s.default_channel, "----------------\n"+msg)
            else:
                await self.client.send_message(s.default_channel, msg)
            self.lastMsgAuthor[s.default_channel] = self.client.user

            # Limit the message rate
            await asyncio.sleep(0.1)

