#!/usr/bin/env python3

# Twitch IRC variables
host_server = "irc.twitch.tv"
host_port = 6667
bot_handle = "" # must be lowercase
bot_password = "" # visit http://twitchapps.com/tmi/ to obtain
channel = "#" # first character is a hashtag

# Twitch limits user messages to 20 messages every 30 seconds. Failure to obey this results in 8-hour ban.
rate = (20/30)
# If a moderator of the channel, the limit is 100 messages / 30 seconds
# Worry about that if a 2/3 second delay ever becomes an issue.
# This needs to be balanced with actions that send multiple commands to the IRC server

# Social media settings
xbox_handle = ""
playstation_handle = ""
#playstation_trophy_url = "" # need to sign up first at playstation's site
#steam_url = ""
twitter_url = ""
youtube_url = ""

# Language strike out settings
# Note that the strike count only lasts until bot restarts. Bannings last until cleared in Twitch settings.

# System set up:
# On first offenses, the message is deleted. User is allowed to continue to send messages.
# If user used 50% or more of the allowed chances, the user is given a X-second timeout per below
# When the strike count is reached, the user is banned from the channel

# Ban user on this strike number
strikes_until_ban = 5
# Length of silence timeout for repeated strikes in seconds (default 600 seconds = 10 minutes)
strikes_timeout_duration = 600

# Suppress messages in all uppercase letters with at least this many characters:
uppercase_message_suppress_length = 20

# Raffle settings
# Have subscribers count as this many entries when they enter a raffle pool
raffle_subscriber_entries=5
