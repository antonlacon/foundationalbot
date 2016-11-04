#!/usr/bin/env python3

# Foundational IRC Bot for Twitch.tv

# Copyright 2015-2016 Ian Leonard <antonlacon@gmail.com>
#
# This file is foundationalbot.py and is part of the Foundational IRC Bot project.
#
# foundationalbot.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# foundationalbot.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with foundationalbot.py. If not, see <http://www.gnu.org/licenses/>.

# ToDo:
# Proper Python formatting
# Add timestamp to self-generated messages - write log function to use for messaging - debug module can do it?
# Timestamp chat messages too?
# finish !schedule support - will need pytz installed (3rd party) or forget timezones altogether?
# Twitter integration? - Twitch website has done this?
# Teach bot to send a whisper - Postponed til Whispers 2.0
# Teach bot to read a whisper - Postponed til Whispers 2.0
# Add website whitelisting - youtube, twitch, wikipedia, ?
# If raffle is active, format the winner's username differently so it'll be seen in terminal log - color?
# Have raffles show subscriber status if that's the case - how long they have followed?
# Timed messages to channel - youtube, twitter, ?
# Add a reset command - resets raffle settings, multi settings, and clears strikeout list
# Stream info commands: uptime, followers, viewers, set status, set game - needs twitch api hookup
# Pull the command parser out of the main loop parser
# Simplify command parser - check user's mod status, or whether broadcaster when looking at command?
# Clean up where variables are declared
# Reconfigure for multiple channels
# Rate limiter for JOIN commands

# Core Modules
import socket 			# IRC networking
import re 			# Regular expression parsing to parse chat messages
import random 			# Random number generator for raffle
from time import sleep 		# sleep() command
from sys import exit 		# exit() command
from datetime import datetime 	# date functions
# Project Modules
import bot_cfg 			# Bot's config file
import language_watchlist 	# Bot's file for monitoring language to take action on
import fb_sql			# SQLite database interaction

### START UP VARIABLES ###

# Command listing for all users - comma separated
public_command_list = [ "!test",
		"!xbl", "!xb1",
		"!psn", "!ps4",
		"!steam",
		"!youtube",
		"!twitter",
		"!schedule",
		"!time" ]

# Follower only commands - comma separated
#follower_command_list = []

# Subscriber only commands - comma separated
#subscriber_command_list = []

# Moderator only commands - comma separated
#moderator_command_list = []

# Editor only commands - comma separated
#editor_command_list = []

# Broadcaster only commands - comma separated
broadcaster_command_list = [ "!quit", "!exit",
				"!raffle",
				"!reconnect",
				"!voice" ]
#				"!multi",

# Channel name is based on broadcaster's name, so use it to determine broadcaster
irc_channel_broadcaster = bot_cfg.channel[1:]

# Twitch limits user messages to 20 messages in 30 seconds. Failure to obey = 8-hr ban.
# Moderators have an increased limit to 100 messages in 30 seconds.
# Script will detect below whether it is a mod and adjust the rate accordingly
message_rate = (20/30)

### IRC COMMANDS ###

# Send a message to the channel
def command_irc_send_message(msg):
	global messages_sent
	irc_socket.send("PRIVMSG {} :{}\r\n".format(bot_cfg.channel, msg).encode("utf-8"))
	messages_sent += 1

# Ban a user from the channel
def command_irc_ban(user):
	command_irc_send_message(".ban {}".format(user))

# Silence a user for X seconds (default 10 minutes)
def command_irc_timeout(user, seconds=600):
	command_irc_send_message(".timeout {}".format(user, seconds))

# Unban or return voice to a user
def command_irc_unban(user):
	command_irc_send_message(".unban {}".format(user))

# JOIN channel
def command_irc_join(channel):
	global messages_sent
	irc_socket.send("JOIN {}\r\n".format(channel).encode("utf-8"))
	messages_sent += 1

# DePART channel
def command_irc_part(channel):
	global messages_sent
	irc_socket.send("PART {}\r\n".format(channel).encode("utf-8"))
	messages_sent += 1

# Answer PING request with PONG
def command_irc_ping_respond():
	global messages_sent
	irc_socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
	messages_sent +=1

# Exit IRC channel
def command_irc_quit(message_rate):
	global messages_sent
	command_irc_send_message("Shutting down.")
	command_irc_part(bot_cfg.channel)

### PARSING VARIABLES AND SUPPORT FUNCTIONS ###

# Regular expressions that will be used frequently so build the regex once to quickly retrieve, use grouping to reuse
#irc_message_regex = re.compile(r"^@badges=[a-zA-Z0-9_,\/]*;color=[#a-fA-F0-9]*;display-name=([a-zA-Z0-9_\-]*);emotes=[a-zA-Z0-9\-:\/,]*;id=[a-f0-9\-]*;mod=\d+;room-id=\d+;sent-ts=\d+;subscriber=(\d+);tmi-sent-ts=\d+;turbo=\d+;user-id=\d+;user-type=(\w*) :(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG (#\w+) :")
irc_message_regex = re.compile(r"^@.*;display-name=([a-zA-Z0-9_\-]*);.*;mod=\d+;.*;subscriber=(\d+);.*;user-type=(\w*) :(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG (#\w+) :")
irc_join_regex = re.compile(r"^:\w+!(\w+)@\w+\.tmi\.twitch\.tv JOIN #\w+")

# Strikeout system implementation
def add_user_strike(db_action, user):
	user_displayname = fb_sql.db_vt_show_displayname(db_action, user)
	user_strike_count = fb_sql.db_vt_show_strikes(db_action, user)
	# hand out the strike and check effects
	user_strike_count += 1

	# If user reaches the strike limit, hand out a ban
	if user_strike_count == bot_cfg.strikes_until_ban:
		command_irc_ban(user)
		print ("LOG: Banned user per strikeout system: " + user)
		command_irc_send_message(user_displayname + " banned per strikeout system.")
		# Delete user from database
		# TODO: make this a maintenance action instead?
		fb_sql.db_vt_delete_user(db_action, user)
	else:
		# Write updated strike count to database
		fb_sql.db_vt_change_strikes(db_action, user)
		print ("LOG: Additional strike added to: " + user + ". User's strike count is: " + str(user_strike_count))

		# If user exceeded half of the allowed strikes, give a longer timeout and message in chat
		if user_strike_count >= (bot_cfg.strikes_until_ban/2):
			command_irc_timeout(user, bot_cfg.strikes_timeout_duration)
			# TODO state how long timeout is in minutes
			command_irc_send_message("Warning: " + user_displayname + " in timeout for chat rule violation." )
			print ("LOG: User " + user + " silenced per strikeout policy.")
		# If user does not have many strikes, clear message(s) and warn
		else:
			command_irc_timeout(user, 1)
			command_irc_send_message("Warning: " + user_displayname + " messages purged for chat rule violation." )
			print ("LOG: Messages from " + user + " purged.")

# Raffle support variables
raffle_active = False
raffle_keyword = None
raffle_contestants = []

# Multistream support variables
#multistream_url = "http://kadgar.net/live/" + broadcaster + "/"
#multistream_url_default = multistream_url

# IRC response buffer (incoming messages)
irc_response_buffer = ""

### INITIALIZE IRC CONNECTION FUNCTION ###
def initialize_irc_connection():

	global active_connection
	global irc_response_buffer
	global irc_socket
	global messages_sent
	initial_connection = False
	messages_sent = 0

	# Connect to Twitch and enter chosen channel
	try:
		irc_socket = socket.socket()
		irc_socket.connect((bot_cfg.host_server, bot_cfg.host_port))
		irc_socket.send("PASS {}\r\n".format(bot_cfg.bot_password).encode("utf-8"))
		irc_socket.send("NICK {}\r\n".format(bot_cfg.bot_handle).encode("utf-8"))
		command_irc_join(bot_cfg.channel)
		initial_connection = True
	except:
		raise

	# Initial login messages
	# FIXME potential unbound while loop; count number of expected messages and abort if it's reached without connecting?
	while initial_connection:
		irc_response_buffer = irc_response_buffer + irc_socket.recv(1024).decode("utf-8")
		irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
		irc_response_buffer = irc_response.pop()

		for message_line in irc_response:
			# Connected to Twitch IRC server but failed to login (bad user/pass)
			if ":tmi.twitch.tv NOTICE * :Login unsuccessful" in message_line:
				print(message_line)
				active_connection = False
				initial_connection = False
			# Last line of a successful login to Twitch
			elif ":tmi.twitch.tv 376 {} :>".format(bot_cfg.bot_handle) in message_line:
				print(message_line)
				# Tell Twitch to send full messaging metadata and not plain IRC messages
				irc_socket.send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n".encode("utf-8"))
				active_connection = True
				initial_connection = False
			else:
				print(message_line)
	# pause for rate limiter and the number of messages sent in login process
	sleep((1 / message_rate) * (messages_sent + 3))

### COMMAND PARSER FUNCTION ###
#def command_parser():
#	pass

### PARSER LOOP FUNCTION ###

# Implement the main parser loop from which IRC messages are understood
def main_parser_loop(db_action):
	# Variables declared outside the function that will change inside the function
	global active_connection
	global bot_active
	global irc_response_buffer
	global message_rate
	global messages_sent
	global raffle_active
	global raffle_keyword
	global raffle_contestants

	# Parser loop
	while active_connection:

		# Messages being received from the IRC server stored in a buffer in case of incomplete messages
		irc_response_buffer = irc_response_buffer + irc_socket.recv(1024).decode("utf-8")
		irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
		irc_response_buffer = irc_response.pop()

		# Count messages sent as a rate limiter to avoid 8-hr global timeout
		messages_sent = 0

		# Timestamp
		now_local_logging = datetime.now().strftime("%Y%m%d %H:%M:%S")

		for message_line in irc_response:

			# Twitch will check that clients are still alive; respond with PONG
			if message_line == "PING :tmi.twitch.tv":
				command_irc_ping_respond()
				print("LOG: Received PING. Sent PONG.")

			# Majority of parsing will be done on PRIVMSGs from the server
			elif re.search(r" PRIVMSG ", message_line):
# Debug option
#				print(message_line)

				# Channel message parsing - other variables possible if grouping is adjusted
				parsed_irc_message = irc_message_regex.search(message_line)
				user_display_name = parsed_irc_message.group(1)
				user_subscriber_status = parsed_irc_message.group(2)
				user_mod_status = parsed_irc_message.group(3) # is this correct?
				username = parsed_irc_message.group(4)
				irc_channel = parsed_irc_message.group(5)
# TODO: Needed for multichannel support
#				irc_channel_broadcaster = irc_channel[1:]
				message = irc_message_regex.sub("", message_line)

				print(now_local_logging + ":" + irc_channel + ":" + username + ": " + message)

				# Add username to database in case message sent before JOIN message
				if fb_sql.db_vt_test_username(db_action, username) == False:
					fb_sql.db_vt_addentry(db_action, username, user_display_name)
				# Viewer may have been added to DB by JOIN message, or changed their displayname; update it
				elif user_display_name != fb_sql.db_vt_show_displayname(db_action, username):
					fb_sql.db_vt_change_displayname(db_action, username, user_display_name)

				# Command Parser - if changing commands, remember to adjust the command listings at top
				if message.startswith("!"):
					# FIXME turn this into a command parser
					msg = message.split(" ")
					# Force to lowercase for parsing
					msg[0] = msg[0].lower()

					# Commands only available to broadcaster
					if msg[0] in broadcaster_command_list and username == irc_channel_broadcaster:

						# Shutting down the bot in a clean manner
						if msg[0] == "!quit" or msg[0] == "!exit":
							print("LOG: Shutting down on commnd from: " + username)
							command_irc_quit(message_rate)
							irc_socket.close()
							active_connection = False
							bot_active = False
						# Tell bot to quit and reconnect - for test purposes
						if msg[0] == "!reconnect":
							print("LOG: Reconnecting to IRC server on command from: " + username)
							command_irc_quit(message_rate)
							irc_socket.close()
							active_connection = False
						# Raffle support commands
						elif msg[0] == "!raffle" and len(msg) > 1:
							msg[1] = msg[1].strip().lower()
							# Setting a watchword to monitor in the channel to look for active viewers
							if msg[1] == "keyword" and len(msg) == 3:
								raffle_keyword = msg[2].strip()
								print("LOG: Raffle keyword set to: " + raffle_keyword)
								command_irc_send_message("Raffle keyword set to: " + raffle_keyword)
								raffle_active = True
							# Reset all raffle settings
							elif msg[1] == "clear":
								print("LOG: Raffle entries cleared.")
								raffle_contestants.clear()
								raffle_winner = None
								raffle_winner_displayname = None
								raffle_keyword = None
								raffle_active = False
								command_irc_send_message("Raffle settings and contestant entries cleared.")
							# Announce number of entries in pool
							elif msg[1] == "count":
								print("LOG: Raffle participants: " + str(len(raffle_contestants)))
								command_irc_send_message("Raffle contestants: " + str(len(raffle_contestants)))
							# Closing raffle to new entries
							elif msg[1] == "close":
								raffle_active = False
								print("LOG: Raffle closed to further entries.")
								command_irc_send_message("Raffle closed to further entries.")
							# Reopens raffle to entries
							elif msg[1] == "reopen":
								raffle_active = True
								print("LOG: Raffle reopened for entries.")
								command_irc_send_message("Raffle reopened.")
							# Selecting a winner from the pool
							elif msg[1] == "winner":
								if len(raffle_contestants) == 0:
									command_irc_send_message("No winners available; raffle pool is empty.")
								else:
									raffle_winner = raffle_contestants[random.randrange(0,len(raffle_contestants),1)]
									raffle_winner_displayname = fb_sql.db_vt_show_displayname(db_action, raffle_winner)
									print("LOG: Raffle winner: " + raffle_winner)
									command_irc_send_message("Raffle winner: " + raffle_winner_displayname + ". Winner's chance was: " + str((1/len(raffle_contestants)*100)) + "%")
									# Only allow winner to win once per raffle
									raffle_contestants[:] = (remaining_contestants for remaining_contestants in raffle_contestants if remaining_contestants != raffle_winner)
						# Supporting multiple streamers
#						elif msg[0] == "!multi":
#							if len(msg) > 1:
#								msg[1] = msg[1].strip().lower()
#								if msg[1] == "add" and len(msg) == 3:
#									multistream_url = multistream_url + msg[2].strip() + "/"
#									print("LOG: Multistream URL set to: " + multistream_url)
#									command_irc_send_message("Multistream URL set to: " + multistream_url)
#								elif msg[1] == "set" and len(msg) == 3:
#									if msg[2].lower() == "default":
#										multistream_url = multistream_url_default
#										print("LOG: Multistream URl reset to default.")
#										command_irc_send_message("Multistream URL reset to default.")
#									else:
#										multistream_url = msg[2].strip()
#										print("LOG: Multistream URL set to: " + multistream_url)
#										command_irc_send_message("Multistream URL set to: " + multistream_url)
#								else:
#									print("LOG: Unknown usage of !multi.")
#									command_irc_send_message("Unknown usage of !multi.")
#							else:
#								command_irc_send_message("Multistream URL is: " + multistream_url)
						# Return voice to a user in a timeout or ban
						elif msg[0] == "!voice" and len(msg) == 2:
							pardoned_user = msg[1].strip().lower()
							command_irc_unban(pardoned_user)

					# Commands available to anyone
					elif msg[0] in public_command_list:

						# Basic test command to see if bot works
						if msg[0] == "!test":
							command_irc_send_message("All systems nominal.")
						# Social media commands
						elif msg[0] == "!xbl" or msg[0] == "!xb1":
							command_irc_send_message("Broadcaster's XBL ID is: " + bot_cfg.xbox_handle)
						elif msg[0] == "!psn" or msg[0] == "!ps4":
							command_irc_send_message("Broadcaster's PSN ID is: " + bot_cfg.playstation_handle)
						elif msg[0] == "!steam":
							command_irc_send_message("Broadcaster's Steam ID is: " + bot_cfg.steam_handle +  " and profile is: " + bot_cfg.steam_url)
						elif msg[0] == "!twitter":
							command_irc_send_message("Broadcaster's twitter url is: " + bot_cfg.twitter_url)
						elif msg[0] == "!youtube":
							command_irc_send_message("Select broadcasts, highlights and other videos may be found on YouTube: " + bot_cfg.youtube_url)
						# State bot's current time and time to next broadcast
						elif msg[0] == "!schedule":
							now_local_day = datetime.now().strftime("%A")
							now_local = datetime.now().strftime("%I:%M%p")
#							now_utc = datetime.utcnow().strftime("%A %I:%M%p")
							command_irc_send_message("Current stream time is: " + now_local_day + " " + now_local + ". Today's schedule is: " + bot_cfg.broadcaster_schedule[now_local_day])
						elif msg[0] == "!time":
							now_local = datetime.now().strftime("%A %I:%M%p")
							command_irc_send_message("Stream time is: " + now_local)

				# Raffle monitor
				# Control with a True/False if raffle is active for faster
				if raffle_active == True:
					if message.strip() == raffle_keyword and username not in raffle_contestants:
						raffle_contestants.append(username)
						print("LOG: " + username + " is entry number " + str(len(raffle_contestants)))

				# Message censor. Employ a strikeout system and ban policy.
				# TODO Control with a True / False if language monitoring is active
				if ( username != irc_channel_broadcaster and
				     user_mod_status == "" ):
					for language_control_test in language_watchlist.prohibited_words:
						if re.search(language_control_test, message):

							add_user_strike(db_action, username)
							print ("LOG: " + username +" earned a strike for violating the language watchlist.")

					# Messages longer than a set length in all uppercase count as a strike
					if ( len(message) >= bot_cfg.uppercase_message_suppress_length and
					     message == message.upper() ):
						add_user_strike(db_action, username)
						print ("LOG: " + username + " earned a timeout for a message in all capitals. Strike added.")

			# Monitor MODE messages to detect if bot gains or loses moderator status
			elif re.search(r" MODE ", message_line):
				if "#" + bot_cfg.channel + " +o " + bot_cfg.bot_handle in message_line:
					print("LOG: Bot gained mod status. Adjusting message rate.")
					message_rate = (100/30)
				elif "#" + bot_cfg.channel + " -o " + bot_cfg.bot_handle in message_line:
					print("LOG: Bot lost mod status. Adjusting message rate.")
					message_rate = (20/30)

			# Handle requests to reconnect to the chat servers from Twitch
			elif re.search(r" RECONNECT ", message_line):
				print("LOG: Reconnecting to server based on message from server.")
				command_irc_quit(message_rate)
				irc_socket.close()
				active_connection = False

			# Add viewers to database on join
			elif re.search(r" JOIN ", message_line):
				# Parse JOIN message to obtain username
				print(message_line)
				parsed_irc_message = irc_join_regex.search(message_line)
				username = parsed_irc_message.group(1)

				# Add username to database if not present
				if fb_sql.db_vt_test_username(db_action, username) == False:
					fb_sql.db_vt_addentry(db_action, username)

			# Drop user status messages in the specific channel (USERSTATE), and the bot's GLOBALUSERSTATE
			elif re.search(r" USERSTATE ", message_line) or \
			re.search(r" GLOBALUSERSTATE ", message_line) or \
			re.search(r" PART ", message_line):
				break

			# Not an IRC message covered elsewhere
			else:
				print(message_line)

			# Rate control on sending messages
			sleep((1 / message_rate) * messages_sent)

### MAIN ###
if __name__ == "__main__":

	# bot_active controls whether the bot should shut down all activities and exit
	# intial_connection puts the bot in the startup login phase
	# active_connection makes the main parser loop active going through server messages

	bot_active = True

	### CONNECT TO SQLITE DATABSE ###
	# Connect to sqlite database and store connection information
	db_connection, db_action = fb_sql.db_initialize()
	# create a Viewers table if it does not already exist
	fb_sql.db_vt_createtable(db_action)
	# count the rows

	while bot_active:

		### START EXTERNAL CONNECTION ###
		initialize_irc_connection()

		### LOOP THROUGH MESSAGES FROM SERVER TO TAKE ACTION ###
		main_parser_loop(db_action)

	# Loop broken; time to close things down
	print( fb_sql.db_vt_show_all(db_action) )
	# give feedback from db - # of rows, change from start?
	fb_sql.db_shutdown(db_connection)
	exit(0)
