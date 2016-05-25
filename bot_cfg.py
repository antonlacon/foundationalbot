#!/usr/bin/env python3

# This file is part of the Foundational IRC Bot project.

# Twitch IRC variables
host_server = "irc.twitch.tv"
host_port = 6667
bot_handle = "" # must be lowercase
bot_password = "" # visit http://twitchapps.com/tmi/ to obtain
channel = "#" # first character is a hashtag

# Stream Schedule
broadcaster_schedule = { "Monday" : "abc",
                        "Tuesday" : "def",
                        "Wednesday" : "ghi",
                        "Thursday" : "jkl",
                        "Friday" : "mno",
                        "Saturday" : "pqr",
                        "Sunday" : "stu" }

# Social media settings
xbox_handle = ""
playstation_handle = ""
#playstation_trophy_url = "" # need to sign up first at playstation's site
steam_handle = ""
steam_url = ""
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
