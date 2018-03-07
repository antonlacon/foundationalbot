#!/usr/bin/env python3
#
# Copyright 2016-2017 Ian Leonard <antonlacon@gmail.com>
#
# This file is config.py and is part of the Foundational IRC Bot project.
#
# config.py is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, version 3 of the License.
#
# config.py is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# config.py. If not, see <http://www.gnu.org/licenses/>.

# All of these variables are set / changed while the Bot is running

# Operating status
active_connection = False
bot_active = False

# Communication Routes
irc_socket = None
db_action = None

# Bot's home channel
bot_channel = None

# List of channels bot is in
channels_present = []

# Twitch limits user messages to 20 messages in 30 seconds. Failure to obey is
# an 8-hour global ban. Moderators have an increased limit to 100 messages in 30
# seconds. The bot will detect whether it is a mod and adjust its rate limit
# accordingly.
#
# Twitch also allows registering a bot as a bot, changing the default allowed
# message rate. See:
# https://discuss.dev.twitch.tv/t/have-a-chat-whisper-bot-let-us-know/10651
message_rate = (20/30)

# Message counter to rate limit messages sent to Twitch
messages_sent = 0

# Raffle variables
# Dictionary of channel:true/false
raffle_active = {}
# Dictionary of channel:keyword
raffle_keyword = {}
