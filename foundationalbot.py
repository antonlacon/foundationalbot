#!/usr/bin/env python3
#
# Foundational IRC Bot for Twitch.tv
# Website: https://github.com/antonlacon/foundationalbot
#
# Copyright 2015-2018 Ian Leonard <antonlacon@gmail.com>
#
# This file is foundationalbot.py and is part of the Foundational IRC Bot
# project.
#
# foundationalbot.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation, version 3 of the License.
#
# foundationalbot.py is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License
# along with foundationalbot.py. If not, see <http://www.gnu.org/licenses/>.

# Core Modules
import socket                   # IRC networking
import re                       # Regex parsing to parse chat messages
from time import sleep          # sleep() command
from sys import exit            # exit() command
from datetime import datetime   # date functions
# Project Modules
import bot_cfg                  # Bot's config file
import config                   # Variables shared between modules
import fb_commands              # Command parser
import fb_irc                   # IRC commands
import fb_sql                   # SQLite database interaction
import language_watchlist       # Collection of words to take action on


### PARSING VARIABLES ###

# Regular expressions that will be used frequently so build the regex once to quickly retrieve, use grouping to reuse
irc_message_regex = re.compile(
    r"^@.*;display-name=(.*?);.*;mod=\d;.*;subscriber=(\d);.*;user-type=(\w*) :(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG (#\w+) :"
    )
irc_join_regex = re.compile(r"^:\w+!(\w+)@\w+\.tmi\.twitch\.tv JOIN #\w+")
irc_userstate_regex = re.compile(r"^@.*;mod=(\d);.* :tmi\.twitch\.tv USERSTATE (#\w+)")

# IRC response buffer (incoming messages)
irc_response_buffer = ""

### SUPPORT FUNCTIONS ###

def add_user_strike(user):
    """ Strikeout system implementation. Adds a strike and checks effects. """
    user_displayname = fb_sql.db_vt_show_displayname(user)
    user_strike_count = fb_sql.db_vt_show_strikes(user)
    # hand out the strike and check effects
    if bot_cfg.strikes_until_ban != 0:
        user_strike_count += 1

    # If user reaches the strike limit, hand out a ban
    if user_strike_count == bot_cfg.strikes_until_ban and bot_cfg.strikes_until_ban != 0:
        fb_irc.command_irc_ban(user)
        print(f"LOG: Banned user per strikeout system: {user}")
        fb_irc.command_irc_send_message(f"{user_displayname} banned per strikeout system.")
    else:
        # Write updated strike count to database
        fb_sql.db_vt_change_strikes(user, user_strike_count)
        print(f"LOG: Additional strike added to: {user}. User's strike count is: {str(user_strike_count)}")

        # If user exceeded half of the allowed strikes, give a longer timeout and message in chat
        if user_strike_count >= (bot_cfg.strikes_until_ban/2) and bot_cfg.strikes_until_ban != 0:
            fb_irc.command_irc_timeout(user, bot_cfg.strikes_timeout_duration)
            fb_irc.command_irc_send_message(
                f"Warning: {user_displayname} in timeout for chat rule violation. {str(bot_cfg.strikes_timeout_duration/60)} minutes."
                )
            print(f"LOG: User {user} silenced per strikeout policy.")
        # If user does not have many strikes, clear message(s) and warn
        else:
            fb_irc.command_irc_timeout(user, 1)
            fb_irc.command_irc_send_message(f"Warning: {user_displayname} messages purged for chat rule violation.")
            print(f"LOG: Messages from {user} purged.")


### NEGOTIATING CONNECTION TO TWITCH ###
def initialize_irc_connection():
    """ Initialize the IRC connection to Twitch """
    irc_response_buffer = ""
    initial_connection = False
    config.messages_sent = 0

    # Connect to Twitch and enter bot's channel
    config.irc_socket = socket.socket()
    config.irc_socket.connect((bot_cfg.host_server, bot_cfg.host_port))
    config.irc_socket.send(f"PASS {bot_cfg.bot_password}\r\n".encode("utf-8"))
    config.irc_socket.send(f"NICK {bot_cfg.bot_handle}\r\n".encode("utf-8"))
    initial_connection = True

    # Join broadcaster's channel
    fb_irc.command_irc_join(bot_cfg.channel)

    # Initial login messages
    # XXX: unbound while loop; count messages and abort if it's reaches a threshold?
    while initial_connection:
        irc_response_buffer = irc_response_buffer + config.irc_socket.recv(1024).decode("utf-8")
        irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
        irc_response_buffer = irc_response.pop()

        for message_line in irc_response:
            print(message_line)
            # Connected to Twitch IRC server but failed to login
            if ":tmi.twitch.tv NOTICE * :Login unsuccessful" in message_line:
                config.active_connection = False
                initial_connection = False
            # Last line of a successful login
            elif f":tmi.twitch.tv 376 {bot_cfg.bot_handle} :>" in message_line:
                # Request full messaging metadata from IRC messages
                config.irc_socket.send(
                    "CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n".encode("utf-8")
                    )
                config.active_connection = True
                initial_connection = False
    # pause for rate limiter and the number of messages sent in login process
    sleep((1 / config.message_rate) * (config.messages_sent + 3))


### PARSER LOOP ###
def main_parser_loop():
    """ The main parser loop that processes messages from the IRC server """
    irc_response_buffer = ""
    bot_is_mod = False

    # Parser loop
    while config.active_connection:

        # Messages being received from the IRC server stored in a buffer in case of incomplete messages
        try:
            irc_response_buffer = irc_response_buffer + config.irc_socket.recv(1024).decode("utf-8")
        except UnicodeDecodeError:
            print("ERR: Unicode decoding error. Message ignored.")
            continue
        irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
        irc_response_buffer = irc_response.pop()

        # Count messages sent as a rate limiter to avoid global timeout
        config.messages_sent = 0

        # Timestamp
        now_local_logging = datetime.now().strftime("%Y%m%d %H:%M:%S")

        for message_line in irc_response:

            # Twitch will check that clients are still alive; respond with PONG
            if message_line == "PING :tmi.twitch.tv":
                fb_irc.command_irc_ping_respond()
                print("LOG: Received PING. Sent PONG.")

            # Majority of parsing will be done on PRIVMSGs from the server
            elif re.search(r" PRIVMSG ", message_line):
# Debug option
#               print(message_line)

                # Channel message parsing; adjust groups for more variables
                try:
                    parsed_irc_message = irc_message_regex.search(message_line)
                    user_display_name = parsed_irc_message.group(1)
                    user_subscriber_status = parsed_irc_message.group(2)
                    user_mod_status = parsed_irc_message.group(3) # is this correct?
                    username = parsed_irc_message.group(4)
                    irc_channel = parsed_irc_message.group(5)
                    irc_channel_broadcaster = irc_channel[1:]
                    message = irc_message_regex.sub("", message_line)
                except:
                    print(f"ERR: {now_local_logging}: Unparsable chat message")
                    print(message_line)
                    continue

                print(f"{now_local_logging}: {irc_channel}: {username}: {message}")

                # Add username to database in case message sent before JOIN message
                if fb_sql.db_vt_test_username(username) == False:
                    fb_sql.db_vt_addentry(username, user_display_name)
                # Viewer may have been added to DB by JOIN message, or changed their displayname; update it
                elif user_display_name != fb_sql.db_vt_show_displayname(username):
                    fb_sql.db_vt_change_displayname(username, user_display_name)

                # Command Parser
                if message.startswith("!"):
                    fb_commands.command_parser(username, user_mod_status, irc_channel, message)

                # Raffle monitor
                if ( config.raffle_active == True and
                     message.strip() == config.raffle_keyword and
                     not fb_sql.db_vt_show_raffle(username) ):

                    # Add user to raffle
                    fb_sql.db_vt_change_raffle(username)
                    print(f"LOG: {username} added to {irc_channel} raffle.")

                # Message censor. Employ a strikeout system and ban policy.
                if ( bot_is_mod == True and
                     username != irc_channel_broadcaster and
                     user_mod_status == "" ):
                    for language_control_test in language_watchlist.prohibited_words:
                        if re.search(language_control_test, message):

                            add_user_strike(username)
                            print(f"LOG: {username} earned a strike for violating the language watchlist.")

                    # Messages longer than set length in all uppercase count as a strike
                    if ( len(message) >= bot_cfg.uppercase_message_suppress_length and
                         message == message.upper() ):
                        add_user_strike(username)
                        print(f"LOG: {username} earned a timeout for a message in all capitals. Strike added.")

            # Monitor MODE messages to detect if bot gains or loses moderator status
            elif re.search(r" MODE ", message_line):
                if f"#{bot_cfg.channel} +o {bot_cfg.bot_handle}" in message_line:
                    print("LOG: Bot gained mod status. Adjusting message rate and monitoring chat.")
                    bot_is_mod = True
                    config.message_rate = (100/30)
                elif f"#{bot_cfg.channel} -o {bot_cfg.bot_handle}" in message_line:
                    print("LOG: Bot lost mod status. Adjusting message rate and no longer moderating chat.")
                    bot_is_mod = False
                    config.message_rate = (20/30)

            # Handle requests to reconnect to the chat servers from Twitch
            elif re.search(r" RECONNECT ", message_line):
                print("LOG: Reconnecting to server based on message from server.")
                fb_irc.command_irc_part(bot_cfg.channel, True)
                fb_irc.command_irc_send_message("Ordered by Twitch to reconnect; back in a jiffy!")
                config.irc_socket.close()
                config.active_connection = False

            # Add viewers to database on join
            elif re.search(r" JOIN ", message_line):
                # Parse JOIN message to obtain username
                parsed_irc_message = irc_join_regex.search(message_line)
                username = parsed_irc_message.group(1)

                # Add username to database if not present
                if fb_sql.db_vt_test_username(username) == False:
                    fb_sql.db_vt_addentry(username)

            # Check USERSTATE for moderator status
            elif re.search(r" USERSTATE ", message_line):
                parsed_irc_message = irc_userstate_regex.search(message_line)
                user_mod_status = parsed_irc_message.group(1)
                irc_channel = parsed_irc_message.group(2)

                if user_mod_status == "1" and bot_is_mod == False:
                    print("LOG: Bot gained mod status. Adjusting message rate and monitoring chat.")
                    bot_is_mod = True
                    config.message_rate = (100/30)
                elif user_mod_status == "0" and bot_is_mod == True:
                    print("LOG: Bot lost mod status. Adjusting message rate and no longer moderating chat.")
                    bot_is_mod = False
                    config.message_rate = (20/30)

            # Ignore the following:
            # CLEARCHAT: Viewer's chat messages being purged
            # GLOBALUSERSTATE: ?
            # HOSTTARGET: Host mode being turned on/off
            # NOTICE: ?
            # PART: People leaving the chat room
            # ROOMSTATE: Room status (slow-mode, sub-only, etc)
            elif re.search(r" CLEARCHAT ", message_line) or \
            re.search(r" GLOBALUSERSTATE ", message_line) or \
            re.search(r" HOSTTARGET ", message_line) or \
            re.search(r" NOTICE ", message_line) or \
            re.search(r" PART ", message_line) or \
            re.search(r" ROOMSTATE ", message_line):
                break

            # Not an IRC message covered elsewhere
            else:
                print(message_line)

# Database debugging
#           print(fb_sql.db_vt_show_all())

            # Rate control on sending messages
#           print(f"Messages sent: {str(config.messages_sent)}")
            sleep((1 / config.message_rate) * config.messages_sent)

### MAIN ###
if __name__ == "__main__":

    # config.bot_active controls whether the bot should shut down all activities and exit
    # intial_connection puts the bot in the startup login phase
    # config.active_connection makes the main parser loop active going through server messages

    config.bot_active = True

    ### CONNECT TO SQLITE DATABASE ###
    # Connect to sqlite database and store connection information
    db_connection = fb_sql.db_initialize()
    # create a Viewers table if it does not already exist
    fb_sql.db_vt_createtable()
    # count the rows

    while config.bot_active:

        ### START EXTERNAL CONNECTION ###
        initialize_irc_connection()

        ### LOOP THROUGH MESSAGES FROM SERVER TO TAKE ACTION ###
        main_parser_loop()

    # Loop broken; time to close things down
    print(fb_sql.db_vt_show_all())
    # TODO give feedback from db - # of rows, change from start?
    fb_sql.db_shutdown(db_connection)
    exit(0)
