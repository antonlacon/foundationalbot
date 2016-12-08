#!/usr/bin/env python3
#
# Foundational IRC Bot for Twitch.tv
# Website: https://github.com/antonlacon/foundationalbot
#
# Copyright 2015-2016 Ian Leonard <antonlacon@gmail.com>
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

""" ToDo:
	Add timestamp to self-generated messages - write log function to use for messaging - debug module can do it?
	finish !schedule support - will need pytz installed (3rd party) or forget timezones altogether?
	Twitter integration? - Twitch website has done this?
	Teach bot to send/receive whispers - Postponed til Whispers 2.0
	Add website whitelisting - youtube, twitch, wikipedia, ?
	If raffle is active, format the winner's username differently so it'll be seen in terminal log - color?
	Have raffles show subscriber status if that's the case - how long they have followed?
	Timed messages to channel - youtube, twitter, ?
	Add a reset command - resets raffle settings, multi settings, and clears strikeout list
	Stream info commands: uptime, followers, viewers, set status, set game - needs twitch api hookup
	Pull the command parser out of the main loop parser
	Simplify command parser - check user's mod status, or whether broadcaster when looking at command?
	Reconfigure for multiple channels
		Activate !join and !leave commands after multichannel is more fully implemented (mod monitoring)
		Adjust RECONNECT once command_irc_send_message accepts channel assignment
		Only join bot's channel on initial login - move other logins to pre-parser loop
		Bot's op status in each channel
		Admin commands
		Change sleep method to account for whether it was a mod command sleep, or regular user
		Strikes on a per channel basis
		Use a 'channels' db table to track this?
	Replace the sleep system with a date to determine when the next message or command is allowed?
		Build a command queue into that?
	Add boolean for adding/removing to the channel list for the join/part irc commands
"""

# Core Modules
import socket 			# IRC networking
import re 			# Regular expression parsing to parse chat messages
import random 			# Random number generator for raffle
from time import sleep 		# sleep() command
from sys import exit 		# exit() command
from datetime import datetime 	# date functions
# Project Modules
import bot_cfg 			# Bot's config file
import config			# Variables shared between modules
import fb_irc			# IRC commands
import fb_sql			# SQLite database interaction
import language_watchlist 	# Bot's file for monitoring language to take action on

### START UP VARIABLES ###

# Bot's home channel
bot_channel = "#" + bot_cfg.bot_handle

# Command listing for all users - comma separated
public_command_list = [ "!test",
		"!xbl", "!xb1",
		"!psn", "!ps4",
		"!steam",
		"!youtube",
		"!twitter",
		"!schedule",
		"!time" ]

# Broadcaster only commands - comma separated
broadcaster_command_list = [ "!quit", "!exit",
				"!raffle",
				"!reconnect",
				"!voice" ]
#				"!multi",

### PARSING VARIABLES ###

# Regular expressions that will be used frequently so build the regex once to quickly retrieve, use grouping to reuse
irc_message_regex = re.compile(r"^@.*;display-name=(.*?);.*;mod=\d;.*;subscriber=(\d);.*;user-type=(\w*) :(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG (#\w+) :")
irc_join_regex = re.compile(r"^:\w+!(\w+)@\w+\.tmi\.twitch\.tv JOIN #\w+")
irc_userstate_regex = re.compile(r"^@.*;mod=(\d);.* :tmi\.twitch\.tv USERSTATE (#\w+)")

# IRC response buffer (incoming messages)
irc_response_buffer = ""

### SUPPORT FUNCTIONS ###

def add_user_strike(db_action, irc_socket, user):
	""" Strikeout system implementation. Adds a strike and checks effects. """
	user_displayname = fb_sql.db_vt_show_displayname(db_action, user)
	user_strike_count = fb_sql.db_vt_show_strikes(db_action, user)
	# hand out the strike and check effects
	user_strike_count += 1

	# If user reaches the strike limit, hand out a ban
	if user_strike_count == bot_cfg.strikes_until_ban:
		fb_irc.command_irc_ban(irc_socket, user)
		print ("LOG: Banned user per strikeout system: " + user)
		fb_irc.command_irc_send_message(irc_socket, user_displayname + " banned per strikeout system.")
	else:
		# Write updated strike count to database
		fb_sql.db_vt_change_strikes(db_action, user, user_strike_count)
		print ("LOG: Additional strike added to: " + user + ". User's strike count is: " + str(user_strike_count))

		# If user exceeded half of the allowed strikes, give a longer timeout and message in chat
		if user_strike_count >= (bot_cfg.strikes_until_ban/2):
			fb_irc.command_irc_timeout(irc_socket, user, bot_cfg.strikes_timeout_duration)
			fb_irc.command_irc_send_message(irc_socket, "Warning: " + user_displayname + " in timeout for chat rule violation." + str(bot_cfg.strikes_timeout_duration/60) + " minutes." )
			print ("LOG: User " + user + " silenced per strikeout policy.")
		# If user does not have many strikes, clear message(s) and warn
		else:
			fb_irc.command_irc_timeout(irc_socket, user, 1)
			fb_irc.command_irc_send_message(irc_socket, "Warning: " + user_displayname + " messages purged for chat rule violation." )
			print ("LOG: Messages from " + user + " purged.")

### NEGOTIATING CONNECTION TO TWITCH ###
def initialize_irc_connection():
	""" Initialize the IRC connection to Twitch """
	global active_connection
	global irc_response_buffer
	global irc_socket
	initial_connection = False
	config.messages_sent = 0

	# Connect to Twitch and enter bot's channel
	irc_socket = socket.socket()
	irc_socket.connect((bot_cfg.host_server, bot_cfg.host_port))
	irc_socket.send("PASS {}\r\n".format(bot_cfg.bot_password).encode("utf-8"))
	irc_socket.send("NICK {}\r\n".format(bot_cfg.bot_handle).encode("utf-8"))
	if bot_channel in config.channels_present:
		fb_irc.command_irc_join(irc_socket, bot_channel, True)
	else:
		fb_irc.command_irc_join(irc_socket, bot_channel)
	initial_connection = True

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
			# Last line of a successful login
			elif ":tmi.twitch.tv 376 {} :>".format(bot_cfg.bot_handle) in message_line:
				print(message_line)
				# Tell Twitch to send full messaging metadata and not plain IRC messages
				irc_socket.send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n".encode("utf-8"))
				active_connection = True
				initial_connection = False
			else:
				print(message_line)
	# pause for rate limiter and the number of messages sent in login process
	sleep((1 / config.message_rate) * (config.messages_sent + 3))

### PARSER LOOP ###
def main_parser_loop(db_action):
	""" The main parser loop that processes messages from the IRC server """

	# Variables declared outside the function that will change inside the function
	global active_connection
	global bot_active
	global irc_response_buffer

	bot_is_mod = False

	# Join desired channels - need to read responses?
	if len(config.channels_present) > 1:
		for channel in config.channels_present:
			if channel is not bot_channel:
				fb_irc.command_irc_join(irc_socket, channel, True)
	# TODO drop this else clause after multichannel active
	else:
		fb_irc.command_irc_join(irc_socket, bot_cfg.channel)

	# Parser loop
	while active_connection:

		# Messages being received from the IRC server stored in a buffer in case of incomplete messages
		try:
			irc_response_buffer = irc_response_buffer + irc_socket.recv(1024).decode("utf-8")
		except UnicodeDecodeError:
			print("ERR: Unicode decoding error. Message ignored.")
			continue
		irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
		irc_response_buffer = irc_response.pop()

		# Count messages sent as a rate limiter to avoid 8-hr global timeout
		config.messages_sent = 0

		# Timestamp
		now_local_logging = datetime.now().strftime("%Y%m%d %H:%M:%S")

		for message_line in irc_response:

			# Twitch will check that clients are still alive; respond with PONG
			if message_line == "PING :tmi.twitch.tv":
				fb_irc.command_irc_ping_respond(irc_socket)
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
				irc_channel_broadcaster = irc_channel[1:]
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
					# TODO turn this into a command parser
					msg = message.split(" ")
					# Force to lowercase for parsing
					msg[0] = msg[0].lower()

					# Commands only available to broadcaster
					if msg[0] in broadcaster_command_list and username == irc_channel_broadcaster:

						# Leave channel from message
						if msg[0] == "!leave" and irc_channel == bot_channel:
							command_irc_send_message(irc_channel, "So long, and thanks for all the fish!")
							command_irc_part(irc_channel)
						# Shutting down the bot in a clean manner
						elif msg[0] == "!quit" or msg[0] == "!exit":
							print("LOG: Shutting down on commnd from: " + username)
							fb_irc.command_irc_quit(irc_socket)
							irc_socket.close()
							active_connection = False
							bot_active = False
						# Tell bot to quit and reconnect - for test purposes
						if msg[0] == "!reconnect":
							print("LOG: Reconnecting to IRC server on command from: " + username)
							for channel in config.channels_present:
								# TODO uncomment when message goes to each channel individually
								#fb_irc.command_irc_send_message(irc_socket, "Ordered to reconnect; will return shortly!")
								fb_irc.command_irc_part(irc_socket, channel, True)
							irc_socket.close()
							active_connection = False
						# Raffle support commands
						elif msg[0] == "!raffle" and len(msg) > 1:
							msg[1] = msg[1].strip().lower()
							# Setting a watchword to monitor in the channel to look for active viewers
							if msg[1] == "keyword" and len(msg) == 3:
								# Reset raffle status as new keyword entered
								fb_sql.db_vt_reset_all_raffle(db_action)
								config.raffle_keyword[irc_channel] = msg[2].strip()
								print("LOG: Raffle keyword set to: " + config.raffle_keyword[irc_channel])
								fb_irc.command_irc_send_message(irc_socket, "Raffle keyword set to: " + config.raffle_keyword[irc_channel])
								config.raffle_active[irc_channel] = True
							# Reset all raffle settings
							elif msg[1] == "clear":
								print("LOG: Raffle entries cleared.")
								fb_sql.db_vt_reset_all_raffle(db_action)
								raffle_winner = None
								raffle_winner_displayname = None
								config.raffle_keyword[irc_channel] = None
								config.raffle_active[irc_channel] = False
								fb_irc.command_irc_send_message(irc_socket, "Raffle settings and contestant entries cleared.")
							# Announce number of entries in pool
							elif msg[1] == "count":
								print("LOG: Raffle participants: " + str(len(fb_sql.db_vt_show_all_raffle(db_action))))
								fb_irc.command_irc_send_message(irc_socket, "Raffle contestants: " + str(len(fb_sql.db_vt_show_all_raffle(db_action))))
							# Closing raffle to new entries
							elif msg[1] == "close":
								config.raffle_active[irc_channel] = False
								print("LOG: Raffle closed to further entries.")
								fb_irc.command_irc_send_message(irc_socket, "Raffle closed to further entries.")
							# Reopens raffle to entries
							elif msg[1] == "reopen":
								config.raffle_active[irc_channel] = True
								print("LOG: Raffle reopened for entries.")
								fb_irc.command_irc_send_message(irc_socket, "Raffle reopened.")
							# Selecting a winner from the pool
							elif msg[1] == "winner":
								# FIXME: is this limited to channel's raffle?
								raffle_contestants = fb_sql.db_vt_show_all_raffle(db_action)
								if len(raffle_contestants) == 0:
									fb_irc.command_irc_send_message(irc_socket, "No winners available; raffle pool is empty.")
								else:
									raffle_winner = raffle_contestants[random.randrange(0,len(raffle_contestants),1)]
									raffle_winner = raffle_winner[0]
									raffle_winner_displayname = fb_sql.db_vt_show_displayname(db_action, raffle_winner)
									print("LOG: Raffle winner: " + raffle_winner)
									fb_irc.command_irc_send_message(irc_socket, "Raffle winner: " + raffle_winner_displayname + ". Winner's chance was: " + str((1/len(raffle_contestants)*100)) + "%")
									# Only allow winner to win once per raffle
									fb_sql.db_vt_change_raffle(db_action, raffle_winner)
						# Supporting multiple streamers
#						elif msg[0] == "!multi":
							# Multistream support variables
#							multistream_url = "http://kadgar.net/live/" + irc_channel_broadcaster + "/"
#							multistream_url_default = multistream_url
#
#							if len(msg) > 1:
#								msg[1] = msg[1].strip().lower()
#								if msg[1] == "add" and len(msg) == 3:
#									multistream_url = multistream_url + msg[2].strip() + "/"
#									print("LOG: Multistream URL set to: " + multistream_url)
#									fb_irc.command_irc_send_message(irc_socket, "Multistream URL set to: " + multistream_url)
#								elif msg[1] == "set" and len(msg) == 3:
#									if msg[2].lower() == "default":
#										multistream_url = multistream_url_default
#										print("LOG: Multistream URl reset to default.")
#										fb_irc.command_irc_send_message(irc_socket, "Multistream URL reset to default.")
#									else:
#										multistream_url = msg[2].strip()
#										print("LOG: Multistream URL set to: " + multistream_url)
#										fb_irc.command_irc_send_message(irc_socket, "Multistream URL set to: " + multistream_url)
#								else:
#									print("LOG: Unknown usage of !multi.")
#									fb_irc.command_irc_send_message(irc_socket, "Unknown usage of !multi.")
#							else:
#								fb_irc.command_irc_send_message(irc_socket, "Multistream URL is: " + multistream_url)
						# Return voice to a user in a timeout or ban
						elif msg[0] == "!voice" and len(msg) == 2:
							pardoned_user = msg[1].strip().lower()
							fb_irc.command_irc_unban(irc_socket, pardoned_user)

					# Commands available to anyone
					elif msg[0] in public_command_list:

						# Basic test command to see if bot works
						if msg[0] == "!test":
							fb_irc.command_irc_send_message(irc_socket, "All systems nominal.")
						# Join a channel on request
						elif msg[0] == "!join" and irc_channel == bot_channel:
							fb_irc.command_irc_send_message(irc_channel, "Joining: #" + username)
							fb_irc.command_irc_join("#" + username)
						# Social media commands
						elif msg[0] == "!xbl" or msg[0] == "!xb1":
							fb_irc.command_irc_send_message(irc_socket, "Broadcaster's XBL ID is: " + bot_cfg.xbox_handle)
						elif msg[0] == "!psn" or msg[0] == "!ps4":
							fb_irc.command_irc_send_message(irc_socket, "Broadcaster's PSN ID is: " + bot_cfg.playstation_handle)
						elif msg[0] == "!steam":
							fb_irc.command_irc_send_message(irc_socket, "Broadcaster's Steam ID is: " + bot_cfg.steam_handle +  " and profile is: " + bot_cfg.steam_url)
						elif msg[0] == "!twitter":
							fb_irc.command_irc_send_message(irc_socket, "Broadcaster's twitter url is: " + bot_cfg.twitter_url)
						elif msg[0] == "!youtube":
							fb_irc.command_irc_send_message(irc_socket, "Select broadcasts, highlights and other videos may be found on YouTube: " + bot_cfg.youtube_url)
						# State bot's current time and time to next broadcast
						elif msg[0] == "!schedule":
							now_local_day = datetime.now().strftime("%A")
							now_local = datetime.now().strftime("%I:%M%p")
#							now_utc = datetime.utcnow().strftime("%A %I:%M%p")
							fb_irc.command_irc_send_message(irc_socket, "Current stream time is: " + now_local_day + " " + now_local + ". Today's schedule is: " + bot_cfg.broadcaster_schedule[now_local_day])
						elif msg[0] == "!time":
							now_local = datetime.now().strftime("%A %I:%M%p")
							fb_irc.command_irc_send_message(irc_socket, "Stream time is: " + now_local)

				# Raffle monitor
				if ( irc_channel in config.raffle_active and
				     config.raffle_active[irc_channel] == True and
				     message.strip() == config.raffle_keyword[irc_channel] and
				     not fb_sql.db_vt_show_raffle(db_action, username) ):
					fb_sql.db_vt_change_raffle(db_action, username)
					print("LOG: " + username + " added to " + irc_channel + "raffle." )

				# Message censor. Employ a strikeout system and ban policy.
				if ( bot_is_mod == True and
				     username != irc_channel_broadcaster and
				     user_mod_status == "" ):
					for language_control_test in language_watchlist.prohibited_words:
						if re.search(language_control_test, message):

							add_user_strike(db_action, irc_socket, username)
							print ("LOG: " + username +" earned a strike for violating the language watchlist.")

					# Messages longer than a set length in all uppercase count as a strike
					if ( len(message) >= bot_cfg.uppercase_message_suppress_length and
					     message == message.upper() ):
						add_user_strike(db_action, irc_socket, username)
						print ("LOG: " + username + " earned a timeout for a message in all capitals. Strike added.")

			# Monitor MODE messages to detect if bot gains or loses moderator status
			elif re.search(r" MODE ", message_line):
				if "#" + bot_cfg.channel + " +o " + bot_cfg.bot_handle in message_line:
					print("LOG: Bot gained mod status. Adjusting message rate and monitoring chat.")
					bot_is_mod = True
					config.message_rate = (100/30)
				elif "#" + bot_cfg.channel + " -o " + bot_cfg.bot_handle in message_line:
					print("LOG: Bot lost mod status. Adjusting message rate and no longer moderating chat.")
					bot_is_mod = False
					config.message_rate = (20/30)

			# Handle requests to reconnect to the chat servers from Twitch
			elif re.search(r" RECONNECT ", message_line):
				print("LOG: Reconnecting to server based on message from server.")
				for channel in config.channels_present:
					fb_irc.command_irc_part(irc_socket, bot_cfg.channel, True)
#					fb_irc.command_irc_send_message(irc_socket, "Ordered to reconnect; will return shortly!")
				irc_socket.close()
				active_connection = False

			# Add viewers to database on join
			elif re.search(r" JOIN ", message_line):
				# Parse JOIN message to obtain username
				parsed_irc_message = irc_join_regex.search(message_line)
				username = parsed_irc_message.group(1)

				# Add username to database if not present
				if fb_sql.db_vt_test_username(db_action, username) == False:
					fb_sql.db_vt_addentry(db_action, username)

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
			# PART: People leaving the chat room
			# GLOBALUSERSTATE: ?
			# HOSTTARGET: Host mode being turned on/off
			# CLEARCHAT: Viewer's chat messages being purged
			# ROOMSTATE: Room status (slow-mode, sub-only, etc)
			# NOTICE: ?
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
#			print( fb_sql.db_vt_show_all(db_action) )

			# Rate control on sending messages
#			print("Messages sent: " + str(config.messages_sent))
			sleep((1 / config.message_rate) * config.messages_sent)

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
