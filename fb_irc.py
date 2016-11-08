#!/usr/bin/env python3
#
# Copyright 2016 Ian Leonard <antonlacon@gmail.com>
#
# This file is fb_irc.py and is part of the Foundational IRC Bot for Twitch.tv
# project.
#
# fb_irc.py is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, version 3 of the License.
#
# fb_irc.py is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# fb_irc.py. If not, see <http://www.gnu.org/licenses>.

""" TODO:
	Is the bot_cfg import necessary after multichannel?
"""

# Core Modules
from time import sleep	# sleep() command
# Project Modules
import bot_cfg		# Bot configuration
import config		# Variables shared between modules

### IRC COMMANDS ###

def command_irc_send_message(irc_socket, msg):
	""" Send a message to the specified channel """
	irc_socket.send("PRIVMSG {} :{}\r\n".format(bot_cfg.channel, msg).encode("utf-8"))
	config.messages_sent += 1

def command_irc_ban(irc_socket, user):
	""" Ban a user from the specified channel """
	command_irc_send_message(irc_socket, ".ban {}".format(user))

def command_irc_timeout(irc_socket, user, seconds=600):
	""" Silence a user in the specified channel for X seconds (default 10 minutes) """
	command_irc_send_message(irc_socket, ".timeout {}".format(user, seconds))

def command_irc_unban(irc_socket, user):
	""" Unban or unsilence a user in the specified channel """
	command_irc_send_message(irc_socket, ".unban {}".format(user))

def command_irc_join(irc_socket, channel):
	""" Join specified channel """
	irc_socket.send("JOIN {}\r\n".format(channel).encode("utf-8"))
	config.channels_present.append(channel)
	config.messages_sent += 1
	# Rate limit of 50 JOINs in 15 seconds or about 3 per second
	sleep( 1 / (50 / 15))

def command_irc_part(irc_socket, channel):
	""" Depart specified channel """
	irc_socket.send("PART {}\r\n".format(channel).encode("utf-8"))
	config.channels_present.remove(channel)
	config.messages_sent += 1

def command_irc_ping_respond(irc_socket):
	""" Response to PINGs from the server """
	irc_socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
	config.messages_sent += 1

def command_irc_quit(irc_socket):
	""" Leave channel with a departure message """
	command_irc_send_message(irc_socket, "Shutting down.")
	command_irc_part(irc_socket, bot_cfg.channel)

def command_irc_reconnect(irc_socket, channel):
	""" Leave channel without removing from channel list """
	irc_socket.send("PART {}\r\n".format(channel).encode("utf-8"))
	config.messages_sent += 1
