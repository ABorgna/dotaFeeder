import asyncio
import discord
import logging
import os.path
import pickle
import shlex
from collections import defaultdict
from feeder import DotaFeeder
from time import sleep

from pprint import pprint

class DiscordBot:

    PICKLE_FILE = "discordbot_status.pickle"

    def __init__(self, token, updatesPoolingInterval,
                 updatesFetchBlogpost=True, updatesFetchBelvedere=True):
        self.token = token

        self.feeder = DotaFeeder(updatesPoolingInterval,
                                 updatesFetchBlogpost,
                                 updatesFetchBelvedere)
        self.feeder.addListener(self.updateListener)

        self.client = discord.Client()
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.pendingUpdates = []

        self._loadPickle()

    def run(self):
        running = True
        while running:
            try:
                self.feeder.start()
                self.client.run(self.token)
                running = False
            except:
                logging.exception("DiscordBot crashed, restarting in a minute")
                self.feeder.stop()
                sleep(60)
        self._savePickle()

    async def on_ready(self):
        logging.info('Logged in as %s - %s', self.client.user.name, self.client.user.id)

        self.pendingUpdates.sort(key=lambda x: x.time)
        for e in self.pendingUpdates[-4:]:
            await self.updateListener(e)
        self.pendingUpdates = []

    async def on_message(self, msg):
        logging.debug('Message from %s@%s: %s', msg.author, msg.channel, msg.content)
        if msg.author == self.client.user:
            return

        userMention = self.client.user.mention

        msg.content = msg.content.strip()
        if msg.content.startswith(userMention):
            logging.info('Command from %s@%s: %s', msg.author, msg.channel, msg.content)

            content = msg.content[len(userMention):]
            cmd = shlex.split(content)
            await self._parseCommand(cmd, msg)

    async def on_server_join(self, server):
        msg = "Hello! I'm " + self.client.user.name + "\n" + \
              "Use '" + self.client.user.mention + " help' to get the available commands"
        await self.client.send_message(server.default_channel, msg)

    async def updateListener(self, event):
        if not self.client.is_logged_in:
            logging.info('Queuing update until discord is logged')
            self.pendingUpdates.append(event)
            return

        for s in self.client.servers:
            postUpdates = self.pickle["serverConfig"][s.id].get("postUpdates", True)
            if not postUpdates:
                continue

            channel = self.pickle["serverConfig"][s.id].get("updatesChannel", s.default_channel)
            callEveryone = self.pickle["serverConfig"][s.id].get("callEveryone", False)

            prefix = "@everyone " if callEveryone else ""
            prefix += "A new update is here!\n"
            await self._postUpdate(event, channel, prefix)

    # Utils

    def _loadPickle(self):
        if os.path.exists(self.PICKLE_FILE):
            with open(self.PICKLE_FILE,'rb') as h:
                self.pickle = pickle.load(h)
        else:
            self.pickle = {
                "serverConfig": defaultdict(dict)
            }

    def _savePickle(self):
        with open(self.PICKLE_FILE,'wb') as h:
            pickle.dump(self.pickle, h)

    async def _postUpdate(self, event, channel, prefix=""):
        if event is None:
            return

        msg = prefix + \
              event.title + "\n" + \
              event.link + "\n" + \
              "\n" + \
              event.description + "\n"

        await self.client.send_message(channel, msg)

    # Commands

    async def _parseCommand(self, cmd, msg):
        if not len(cmd):
            pass
        command = cmd[0].lower()
        args = cmd[1:]

        # TODO: permissions
        if command == 'help'.lower():
            await self._cmdHelp(args, msg)

        elif command == 'adminHelp'.lower():
            await self._cmdAdminHelp(args, msg)

        elif command == 'blog'.lower():
            event = self.feeder.getLastEvent("blogpost")
            await self._postUpdate(event, msg.channel)

        elif command == 'patch'.lower():
            event = self.feeder.getLastEvent("belvedere")
            await self._postUpdate(event, msg.channel)

        elif command == 'setPostUpdates'.lower():
            await self._cmdSetServerBoolean(args, msg, "postUpdates",
                    "OK, you'll get the news fresh from the oven",
                    "Ohh, I guess you don't care about updates")

        elif command == 'setChannel'.lower():
            await self._cmdSetChannel(args, msg)

        elif command == 'setCallEveryone'.lower():
            await self._cmdSetServerBoolean(args, msg, "callEveryone",
                    "OK, now I will annoy everyone on each update",
                    "OK, I won't annoy you")

        elif command == 'setDetailedPatch'.lower():
            await self._cmdSetServerBoolean(args, msg, "detailedPatch",
                    "OK, I'll post the full patch notes",
                    "OK, I'll just link the patch notes")

    async def _cmdHelp(self, args, msg):
        userMention = self.client.user.mention
        help = "-- Commands --\n" + \
           userMention + " blog: show the last blogpost\n" + \
           userMention + " patch: show the last patch notes\n" + \
           userMention + " help: this\n" + \
           userMention + " adminHelp: list admin-only commands\n"
        await self.client.send_message(msg.channel, help)

    async def _cmdAdminHelp(self, args, msg):
        userMention = self.client.user.mention

        postUpdates = self.pickle["serverConfig"][msg.server.id].get("postUpdates", False)
        postUpdates = "on" if postUpdates else "off"

        currChannel = self.pickle["serverConfig"][msg.server.id].get("updatesChannel", msg.server.default_channel)
        currChannel = currChannel.name

        callEveryone = self.pickle["serverConfig"][msg.server.id].get("callEveryone", False)
        callEveryone = "on" if callEveryone else "off"

        detailedPatch = self.pickle["serverConfig"][msg.server.id].get("detailedPatch", False)
        detailedPatch = "on" if detailedPatch else "off"

        help = "-- Admin commands --\n" + \
           userMention + " setPostUpdates <on|off>: post new updates" + \
                                               " (currently "+postUpdates+")\n" + \
           userMention + " setChannel <channel>: in which channel should I posts the updates" + \
                                               " (currently "+currChannel+")\n" + \
           userMention + " setCallEveryone <on|off>: call everyone when posting a new update" + \
                                               " (currently "+callEveryone+")\n" + \
           userMention + " setDetailedPatch <on|off>: print all the available patch info" + \
                                               " (currently "+detailedPatch+") (WIP)\n"

        await self.client.send_message(msg.channel, help)

    async def _cmdSetServerBoolean(self, args, msg, prop, responseTrue="OK", responseFalse="OK"):
        if not args:
            await self.client.send_message(msg.channel, "Please specify an option")
            return

        if args[0].lower() in ["on", "true"]:
            option = True
        elif args[0].lower() in ["off", "false"]:
            option = False
        else:
            await self.client.send_message(msg.channel, "Please set on or off")
            return

        logging.info("Setting property '%s' = '%s' for server %s", prop, args[0], msg.server.name)
        self.pickle["serverConfig"][msg.server.id][prop] = option
        self._savePickle()

        await self.client.send_message(msg.channel, responseTrue if option else responseFalse)

    async def _cmdSetChannel(self, args, msg):
        if not args:
            await self.client.send_message(msg.channel, "Please specify a new channel")
            return

        channel = discord.utils.get(msg.server.channels, name=args[0])

        if channel is None:
            await self.client.send_message(msg.channel, "Hey! There is no channel named '%s'" % args[0])
            return

        logging.info("Setting channel '%s' for server %s", args[0], msg.server.name)
        self.pickle["serverConfig"][msg.server.id]["updatesChannel"] = channel
        self._savePickle()
        await self.client.send_message(msg.channel, "OK, I'll post updates on %s" % args[0])

