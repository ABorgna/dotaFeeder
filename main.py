#!/bin/python3
import asyncio
import configparser
import functools
import logging
import os.path
import signal
from feeder import DotaFeeder
from discordbot import DiscordBot

CONFIG_FILE = "config.cfg"

#### Read the API keys

config = configparser.ConfigParser()

# Default values
config["general"] = {}
config["general"]["logfile"] = ""
config["general"]["loglevel"] = "INFO"
config["feeder"] = {}
config["feeder"]["polling_interval"] = "30"
config["feeder"]["fetch_blogposts"] = "true"
config["feeder"]["fetch_belvedere"] = "true"
config["discord"] = {}
config["discord"]["token"] = ""

if not os.path.isfile(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as h:
        config.write(h)

# User values
config.read(CONFIG_FILE)

# Logging config
loglevels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
}
configfile = config["general"]["logfile"]
configfile = configfile if len(configfile) else None
level = loglevels.get(config["general"]["loglevel"].upper(), 'INFO')
fmt = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
logging.basicConfig(format=fmt, level=level, filename=configfile)

#### Start feeding
stopFns = []
loop = asyncio.get_event_loop()

feeder = DotaFeeder(config.getint("feeder","polling_interval"),
                    config.getboolean("feeder","fetch_blogposts"),
                    config.getboolean("feeder","fetch_belvedere"))
asyncio.ensure_future(feeder.run())

discord = DiscordBot(config["discord"]["token"], feeder)
asyncio.ensure_future(discord.run())
stopFns.append(discord.stop())

for signame in ('SIGINT', 'SIGTERM'):
    loop.add_signal_handler(getattr(signal, signame), loop.stop)

loop.run_forever()

print("hi!")

for fn in stopFns:
    loop.run_until_complete(fn)

