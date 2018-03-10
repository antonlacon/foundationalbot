#!/usr/bin/env python3
#
# Copyright 2016-2018 Ian Leonard <antonlacon@gmail.com>
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

# Core Modules
from time import sleep      # sleep() command
# Project Modules
from bot_cfg import channel # Only need the channel from bot_cfg
import config               # Variables shared between modules

### IRC COMMANDS ###

def command_irc_send_message(msg):
    """ Send a message to the specified channel """
    config.irc_socket.send(f"PRIVMSG {channel} :{msg}\r\n".encode("utf-8"))
    config.messages_sent += 1

def command_irc_ban(user):
    """ Ban a user """
    command_irc_send_message(f".ban {user}")

def command_irc_timeout(user, seconds=600):
    """ Silence user for X seconds (default 10 minutes) """
    command_irc_send_message(f".timeout {user} {seconds}")

def command_irc_unban(user):
    """ Unban a user """
    command_irc_send_message(f".unban {user}")

def command_irc_untimeout(user):
    """ End a user timeout  """
    command_irc_send_message(f".untimeout {user}")

def command_irc_join(channel, reconnect=False):
    """ Join specified channel """
    config.irc_socket.send(f"JOIN {channel}\r\n".encode("utf-8"))
    config.messages_sent += 1
    # Rate limit of 50 JOINs in 15 seconds or about 3 per second
    sleep( 1 / (50 / 15))

def command_irc_part(channel, reconnect=False):
    """ Depart specified channel """
    config.irc_socket.send(f"PART {channel}\r\n".encode("utf-8"))
    config.messages_sent += 1

def command_irc_ping_respond():
    """ Response to PINGs from the server """
    config.irc_socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    config.messages_sent += 1

def command_irc_quit():
    """ Leave channel with a departure message """
    command_irc_send_message("Shutting down.")
    command_irc_part(channel)

