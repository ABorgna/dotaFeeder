#!/bin/python3
import configparser
import logging
import os.path
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

#### Start the bot
discord = DiscordBot(config["discord"]["token"],
                     config.getint("feeder","polling_interval"),
                     config.getboolean("feeder","fetch_blogposts"),
                     config.getboolean("feeder","fetch_belvedere"))
discord.run()

