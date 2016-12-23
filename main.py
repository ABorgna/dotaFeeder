#!/bin/python3
import configparser
import logging
import os.path
from feeder import DotaFeeder

CONFIG_FILE = "config.cfg"

#### Read the API keys

config = configparser.ConfigParser()

# Default values
config["general"] = {}
config["general"]["logfile"] = ""
config["general"]["loglevel"] = "INFO"
config["general"]["polling_interval"] = "30"
config["keys"] = {}
config["keys"]["discord_api"] = ""

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
fmt = '%(asctime)s:%(levelname)s:%(message)s'
logging.basicConfig(format=fmt, level=level, filename=configfile)

#### Test listener
def listener(event):
    print("------------")
    print(event["type"])
    print(event["link"])
    print(event["title"])
    print()
    print(event["content"])
    print("------------")

#### Start feeding
feeder = DotaFeeder(config.getint("general","polling_interval"))
feeder.addListener(listener)

try:
    feeder.run()
except KeyboardInterrupt:
    pass

