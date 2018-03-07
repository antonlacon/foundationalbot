#!/usr/bin/env python3
# Copyright 2015-2018 Ian Leonard <antonlacon@gmail.com>
#
# This file is fb_commands.py and is part of the Foundational IRC Bot for
# Twitch.tv project.
#
# fb_commands.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# fb_commands.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with fb_commands.py. If not, see <http://www.gnu.org/licenses/>.

# Core Modules
import random                   # Random number generator for raffle
from datetime import datetime   # date functions
# Project Modules
import bot_cfg                  # Bot's config file
import config                   # Variables shared between modules
import fb_irc                   # IRC commands
import fb_sql                   # SQLite database interaction

def command_parser(username, user_mod_status, irc_channel, message):
    irc_channel_broadcaster = irc_channel[1:]

    msg = message.split(" ")
    # force to lowercase for parsing
    msg[0] = msg[0].lower()

    # Bot Administrator Commands
    if username == bot_cfg.bot_admin:
        # Shut down the bot in a clean manner
        if msg[0] == "!quit" or msg[0] == "!exit":
            print(f"LOG: Shutting down on command from: {username}")
            fb_irc.command_irc_quit()
            config.irc_socket.close()
            config.active_connection = False
            config.bot_active = False
        # Quit and reconnect to Twitch (test command)
        elif msg[0] == "!reconnect":
            print(f"LOG: Reconnecting to IRC server on command from: {username}")
            fb_irc.command_irc_send_message("Reconnecting; back in a jiffy!")
            fb_irc.command_irc_part(bot_cfg.channel, True)
            config.irc_socket.close()
            config.active_connection = False

    # Broadcaster Commands
    if username == irc_channel_broadcaster:
        # Raffle support commands
        if msg[0] == "!raffle" and len(msg) > 1:
            msg[1] = msg[1].strip().lower()
            # Setting a watchword to monitor for in the channel to look for active viewers
            if msg[1] == "keyword" and len(msg) == 3:
                # Reset raffle status as new keyword entered
                fb_sql.db_vt_reset_all_raffle()
                config.raffle_keyword[irc_channel] = msg[2].strip()
                print(f"LOG: Raffle keyword set to: {config.raffle_keyword[irc_channel]}")
                fb_irc.command_irc_send_message(f"Raffle keyword set to: {config.raffle_keyword[irc_channel]}")
                config.raffle_active[irc_channel] = True
            # Rest all raffle settings
            elif msg[1] == "clear":
                # TODO limit to channel's raffle
                print("LOG: Raffle entries cleared.")
                fb_sql.db_vt_reset_all_raffle()
                raffle_winner = None
                raffle_winner_displayname = None
                config.raffle_keyword[irc_channel] = None
                config.raffle_active[irc_channel] = None
                fb_irc.command_irc_send_message("Raffle settings and contestant entries cleared.")
            # Announce number of entries in pool
            elif msg[1] == "count":
                print(f"LOG: Raffle participants: {str(len(fb_sql.db_vt_show_all_raffle()))}")
                fb_irc.command_irc_send_message(f"Raffle contestants: {str(len(fb_sql.db_vt_show_all_raffle()))}")
            # Closing raffle to new entries
            elif msg[1] == "close":
                config.raffle_active[irc_channel] = False
                print("LOG: Raffle closed to further entries.")
                fb_irc.command_irc_send_message("Raffle closed to further entries.")
            # Reopens raffle to entries
            elif msg[1] == "reopen":
                config.raffle_active[irc_channel] = True
                print("LOG: Raffle reopened for entries.")
                fb_irc.command_irc_send_message("Raffle reopened.")
            # Selecting a winner from the pool
            elif msg[1] == "winner":
                # TODO is this limited to channel's raffle?
                raffle_contestants = fb_sql.db_vt_show_all_raffle()
                if len(raffle_contestants) == 0:
                    fb_irc.command_irc_send_message("No winners available; raffle pool is empty.")
                else:
                    raffle_winner = raffle_contestants[random.randrange(0,len(raffle_contestants),1)]
                    raffle_winner = raffle_winner[0]
                    raffle_winner_displayname = fb_sql.db_vt_show_displayname(raffle_winner)
                    print(f"LOG: Raffle winner: {raffle_winner}")
                    fb_irc.command_irc_send_message(f"Raffle winner: {raffle_winner_displayname}. Winner's chance was: {str((1/len(raffle_contestants)*100))}%")
                    # Only allow winner to win once per raffle
                    fb_sql.db_vt_change_raffle(raffle_winner)
            # Supporting multiple streamers
#           elif msg[0] == "!multi":
                # Multistream support variables
#               multistream_url = "http://kadgar.net/live/"  + irc_channel_broadcaster + "/"
#               multistream_url_default = multistream_url
#
#               if len(msg) > 1:
#                   msg[1] = msg[1].strip().lower()
#                   if msg[1] == "add" and len(msg) == 3:
#                       multistream_url = multistream_url + msg[2].strip() + "/"
#                       print("LOG: Multistream URL set to: " + multistream_url)
#                       fb_irc.command_irc_send_message("Multistream URL set to: " + multistream_url)
                    # TODO split this into a reset command
#                   if msg[1] == "set" and len(msg) == 3:
#                       if msg[2].lower() == "default":
#                           multistream_url = multistream_url_default
#                           print("LOG: Multistream URL reset to default.")
#                           fb_irc.command_irc_send_message("Multistream URL reset to default.")
#                       else:
#                           multistream_url = msg[2].strip()
#                           print("LOG: Multistream URL set to: " + multistream_url)
#                           fb_irc.command_irc_send_message("Multistream URL set: " + multistream_url)
#                   else:
#                       print("LOG: Unknown usage of !multi.")
#                       fb_irc.command_irc_send_message("Unknown usage of !multi.")
#               else:
#                   fb_irc.command_irc_send_message("Multistream URL is: " + multistream_url)

    # Editor Commands

    # Moderator Commands
#   if user mod status == true or username == broadcaster:
    if username == irc_channel_broadcaster: #or user_mod_status == ???
        if msg[0] == "!voice" and len(msg) == 2:
            pardoned_user = msg[1].strip().lower()
            fb_irc.command_irc_unban(pardoned_user)
            del pardoned_user

    # Subscriber Commands

    # Follower Commands

    # Commands available to everyone
    if msg[0] == "!test":
        fb_irc.command_irc_send_message("All systems nominal.")
    elif (msg[0] == "!xbl" or msg[0] == "!xb1") and bot_cfg.xbox_handle != "":
        fb_irc.command_irc_send_message(f"Broadcaster's XBL ID is: {bot_cfg.xbox_handle}")
    elif (msg[0] == "!psn" or msg[0] == "!ps4") and bot_cfg.playstation_handle != "":
        fb_irc.command_irc_send_message(f"Broadcaster's PSN ID is: {bot_cfg.playstation_handle}")
    elif (msg[0] == "!steam" and bot_cfg.steam_handle != ""):
        fb_irc.command_irc_send_message(f"Broadcaster's Steam ID is: {bot_cfg.steam_handle}")
    elif msg[0] == "!schedule":
        now_local_day = datetime.now().strftime("%A")
        now_local = datetime.now().strftime("%I:%M%p")
        now_utc = datetime.utcnow().strftime("%A %I:%M%p")
        fb_irc.command_irc_send_message(
            f"Current stream time is: {now_local_day} {now_local}. Today's schedule is: {bot_cfg.broadcaster_schedule[now_local_day]}."
            )
    elif msg[0] == "!time":
        now_local = datetime.now().strftime("%A %I:%M%p")
        fb_irc.command_irc_send_message(f"Stream time is: {now_local}")
