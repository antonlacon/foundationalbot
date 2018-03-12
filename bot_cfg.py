#!/usr/bin/env python3
# Copyright 2015-2018 Ian Leonard <antonlacon@gmail.com>
#
# This file is bot_cfg.py and is part of the Foundational IRC Bot for
# Twitch.tv project.
#
# bot_cfg.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the license.
#
# bot_cfg.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bot_cfg.y. If not, see <http://www.gnu.org/licenses/>.

# Twitch IRC variables
host_server = "irc.twitch.tv"
host_port = 6667
bot_admin = "" # the administrator of the bot
bot_handle = "" # must be lowercase
bot_password = "oauth:" # visit http://twitchapps.com/tmi/ to obtain
channel = "#" # first character is a hashtag

# Game Service Handles - Leave empty to disable corresponding !command
xbox_handle = ""
playstation_handle = ""
steam_handle = ""


# Special Effects
# Sound effects are played by VLC, so this bot should run on the streaming machine to make
# use of this feature (or wait for VLC remote control support, which may never come).

# Path to the VLC executable
vlc_bin = "C:\Program Files\VideoLAN\VLC\vlc.exe"

# Invoking multiple sound effects will make them play concurrently. There is no queue or
# blocking for these commands. Stopping playback involves killing VLC via task manager.

# Sound Effect 1 Settings
# The string to listen to for the first sound effect
sfx1_alias = "!sfx1"
# The file path to the first sound effect
sfx1_path = ""

# Sound Effect 2 Settings
sfx2_alias = "!sfx2"
sfx2_path = ""

# Chat Moderation

# Language strike out settings
# Note that the strike count only lasts until bot restarts, unless a database file is used.
# Bans last until cleared in Twitch channel settings.

# System set up:
# On first offenses, the message is deleted. User is allowed to continue to send messages.
# If user used 50% or more of the allowed chances, the user is given a X-second timeout per below.
# When the strike count is reached, the user is banned from the channel.
#
# If the strikes_until_ban is set to 0, no bans or long timeouts will be issued;
# only messages will be removed.

# Ban user on this strike number
strikes_until_ban = 5
# Length of silence timeout for repeated strikes in seconds (default 600 seconds = 10 minutes)
strikes_timeout_duration = 600

# Suppress messages in all uppercase letters with at least this many characters:
uppercase_message_suppress_length = 20
