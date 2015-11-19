#!/usr/bin/env python3

# Foundational IRC Bot for Twitch.tv

# Copyright 2015 Ian Leonard <antonlacon@gmail.com>
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

# For other Python3 based Twitch IRC Bots:
# http://www.instructables.com/id/Twitchtv-Moderator-Bot/?ALLSTEPS
# https://www.sevadus.tv/forums/index.php?/topic/774-simple-python-irc-bot/

# ToDo:
# Add timestamp to self-generated messages - write log function to use for messaging
# Timestamp chat messages too?
# Test if bot is a moderator and set rate that way prior to starting message processing
# Extend privileged users to check for mod status of users in channel?
# Build parser loop into a function
# finish !time support - will need pytz installed (3rd party) or forget timezones altogether?
# Convert the bot to handle multiple channels? - how would it know whos schedule to show?
# Add steam profile page to social media stuff?
# Twitter integration?
# Teach bot to send a whisper - Postponed til Whispers 2.0
# Teach bot to receive a whisper - Postponed til Whispers 2.0
# See what happens if the raffle keyword is set to None
# Upload to Git
# Move command lists to bot_cfg?
# Split commands between broadcaster, moderators, subscribers, anyone
# Convert language watchlist to be for foul language?
# Add website whitelisting - youtube, twitch, wikipedia, ?
# If raffle is active, format the winner's username differently so it'll be seen in terminal log
# Build raffle for subs only
# Figure out flood control or let Twitch global ban take care of it?

import bot_cfg # Bot's config file
import language_watchlist # Bot's file for monitoring language to take action on
import socket # IRC networking
import re # Regular Expression parsing to understand chat messages
import random # Random number generator for raffle support
from time import sleep # sleep() command
from sys import exit # exit() command
from datetime import datetime # date functions for !time command

### START UP VARIABLES ###

# Rate limit tracker
messages_sent = 0

# Command listing for all users - comma separated
command_list = [ "!test",
		"!xbl",
		"!psn",
		"!youtube",
		"!twitter",
		"!time" ]

# Command listing for privileged users only - comma separated
privileged_command_list = [ "!quit", "!exit",
				"!raffle" ]

# Create a list of users that allowed to execute administration commands
privileged_users=[]

# Channel name is based on broadcaster's name, so use it to set first privileged user
broadcaster = bot_cfg.channel[1:]
privileged_users.append(broadcaster)

### IRC COMMANDS ###

# Send a message to the channel
def command_irc_send_message(msg):
	global messages_sent
	irc_socket.send("PRIVMSG {} :{}\r\n".format(bot_cfg.channel, msg).encode("utf-8"))
	messages_sent += 1

# Ban a user from the channel
def command_irc_ban(user):
	global messages_sent
	command_irc_send_message(".ban {}".format(user))
	messages_sent += 1

# Answer PING request with PONG
def command_irc_ping_respond():
	global messages_sent
	irc_socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
	messages_sent +=1

# Exit IRC channel
def command_irc_quit():
	global messages_sent
	irc_socket.send("PART {}\r\n".format(bot_cfg.channel).encode("utf-8"))
	messages_sent += 1

# Silence a user for X seconds (default 10 mins)
def command_irc_timeout(user, seconds=600):
	global messages_sent
	command_irc_send_message(".timeout {}".format(user, seconds))
	messages_sent += 1

### PARSING VARIABLES AND SUPPORT FUNCTIONS ###

# Regular expressions that will be used frequently so build the regex once to quickly retrieve, use grouping to reuse
irc_message_regex = re.compile(r"^@color=[#a-fA-F0-9]*;display-name=([a-zA-Z0-9_\-]*);emotes=[a-zA-Z0-9\-:\/,]*;subscriber=(\d+);turbo=\d+;user-id=\d+;user-type=(\w*) :(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG (#\w+) :")

# User Strike List to monitor banning
user_strike_count = {}

# Strikeout system implementation
def add_user_strike(user):
	if user in user_strike_count or bot_cfg.strikes_until_ban == 1:
		if user_strike_count[user] == (bot_cfg.strikes_until_ban - 1) or bot_cfg.strikes_until_ban == 1:
			command_irc_ban(user)
			print ("LOG: Banned user per strikeout system: " + user)
			command_irc_send_message(user + " banned per strikeout system.")
			del user_strike_count[user]
		else:
			user_strike_count[user] += 1
			print ("LOG: Additional strike added to: " + user + ". User's strike count is: " + str(user_strike_count[user]))

			if user_strike_count[user] >= (bot_cfg.strikes_until_ban/2):
				command_irc_timeout(user, bot_cfg.strikes_timeout_duration)
				# change this username to display name when that is worked out
				command_irc_send_message("Warning: " + user + " in timeout for chat rule violation. Please follow the rules." )
				print ("LOG: User " + user + " silenced per timeout policy.")
			else:
				command_irc_timeout(user, 1)
				print ("LOG: Messages from " + user + " purged.")
	else:
		user_strike_count[user] = 1
		command_irc_timeout(user, bot_cfg.strikes_timeout_duration)
		print ("LOG: User added to strike list: " + user)

# Raffle support variables
raffle_contestants = []
raffle_active = False
raffle_keyword = None

# IRC response buffer for connection
irc_response_buffer = ""

### START EXTERNAL CONNECTION ###

# Connect to Twitch and enter chosen channel
try:
	irc_socket = socket.socket()
	irc_socket.connect((bot_cfg.host_server, bot_cfg.host_port))
	irc_socket.send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n".encode("utf-8"))
	irc_socket.send("PASS {}\r\n".format(bot_cfg.bot_password).encode("utf-8"))
	irc_socket.send("NICK {}\r\n".format(bot_cfg.bot_handle).encode("utf-8"))
	irc_socket.send("JOIN {}\r\n".format(bot_cfg.channel).encode("utf-8"))
	connected = True
except Exception as err_msg:
	print(str(err_msg))
	connected = False

### LOOP THROUGH MESSAGES FROM SERVER TO TAKE ACTION ###

# Main parser
while connected:
	try:
		# Messages being received from the IRC server stored in a buffer in case of incomplete messages
		irc_response_buffer = irc_response_buffer + irc_socket.recv(1024).decode("utf-8")
		irc_response = re.split(r"[~\r\n]+", irc_response_buffer)
		irc_response_buffer = irc_response.pop()

		# Rate limiter to avoid 8-hr globabl timeout for the bot
		messages_sent = 0

		for message_line in irc_response:

			# FIXME Failed login? Stop work. - test this up above? how? - below doesn't work
#			if message_line == "tmi: :tmi.twitch.tv NOTICE * :Error logging in":
#				print("ERROR: Failed to login to server.")
#				irc.socket.close()
#				connected = False

			# Twitch's IRC server will check that clients are still alive. Answer with a PONG to confirm connection.
			if message_line == "PING :tmi.twitch.tv":
				command_irc_ping_respond()
				print("LOG: Received PING. Sent PONG.")

			# Majority of parsing will be done on PRIVMSGs from the server
			elif re.search(r" PRIVMSG ", message_line):
# Debug option
#				print(message_line)

				# Channel message parsing
				parsed_irc_message = irc_message_regex.search(message_line)
				user_display_name = parsed_irc_message.group(1)
				user_subscriber_status = parsed_irc_message.group(2)
				user_mod_status = parsed_irc_message.group(3)
				username = parsed_irc_message.group(4)
				irc_channel = parsed_irc_message.group(5)
				message = irc_message_regex.sub("", message_line)

				print(irc_channel + ":" + username + ": " + message)

				# Command Parser - if adding or subtracting commands, remember to adjust the command listings at the top
				if message.startswith("!"):
					msg = message.split(" ")
					# Force to lowercase for parsing
					msg[0] = msg[0].lower()

					# Commands only available to privileged users
					if msg[0] in privileged_command_list and username in privileged_users:

						# Shutting down the bot in a clean manner
						if msg[0] == "!quit" or msg[0] == "!exit":
							print("LOG: Closing IRC connection based on chat message from: " + username)
							command_irc_send_message("Systems shutting down.")
							command_irc_quit()
							irc_socket.close()
							connected = False

						# Raffle support commands
						if msg[0] == "!raffle" and len(msg) > 1:
							msg[1] = msg[1].strip().lower()
							# Setting a watchword to monitor in the channel to look for active viewers
							if msg[1] == "keyword" and len(msg) > 2:
								raffle_keyword = msg[2].strip()
								print("LOG: Raffle keyword set to: " + raffle_keyword)
								command_irc_send_message("Raffle keyword set to: " + raffle_keyword)
								raffle_active = True
							# Empty all raffle settings
							elif msg[1] == "clear":
								print("LOG: Raffle entries cleared.")
								raffle_contestants.clear()
								raffle_winner = None
								raffle_keyword = None
								raffle_active = False
								command_irc_send_message("Raffle settings and contestant entries cleared.")
							# Announcing how many contestants are in the pool
							elif msg[1] == "count":
								# Needs to differentiate unique users and entries in the case of subscribers?
								print("LOG: Raffle count used.")
								command_irc_send_message("Raffle contestants: " + str(len(raffle_contestants)))
							# Selecting a winner from the pool
							elif msg[1] == "winner":
								print("LOG: Raffle winner used.")
								if len(raffle_contestants) == 0:
									command_irc_send_message("No contestants in raffle pool.")
								else:
									raffle_winner = raffle_contestants[random.randrange(0,len(raffle_contestants),1)]
									# FIXME use the display name?
									print("LOG: Raffle winner: " + raffle_winner)
									command_irc_send_message("Raffle winner: " + raffle_winner)
									# Only allow winner to win one prize per raffle
									raffle_contestants[:] = (remaining_contestants for remaining_contestants in raffle_contestants if remaining_contestants != raffle_winner)

					# Commands available to anyone
					elif msg[0] in command_list:

						# Basic test command to see if bot works
						if msg[0] == "!test":
							command_irc_send_message("All systems nominal.")

						# Social media commands
						if msg[0] == "!xbl":
							command_irc_send_message("Broadcaster's XBL ID is: " + bot_cfg.xbox_handle)
						elif msg[0] == "!psn":
							command_irc_send_message("Broadcaster's PSN IS is: " + bot_cfg.playstation_handle)
						elif msg[0] == "!twitter":
							command_irc_send_message("Broadcaster's twitter url is: " + bot_cfg.twitter_url)
						elif msg[0] == "!youtube":
							command_irc_send_message("Select broadcasts and highlights may be viewed on YouTube at: " + bot_cfg.youtube_url)
						# add Steam page?

						# State streamer's (actually bot's) current time and time to next broadcast
						if msg[0] == "!time":
							now_local = datetime.now().strftime("%A %I:%M%p")
							now_utc = datetime.utcnow().strftime("%A %I:%M%p")
							command_irc_send_message("Current stream time is: " + now_local + " UTC time is: " + now_utc)

				# Raffle monitor
				# Control with a True/False if raffle is active for faster
				if raffle_active == True:
					if message.strip() == raffle_keyword and username not in raffle_contestants:
						# Treat subscribers special by adding a few more chances on their behalf
						if user_subscriber_status == 1 or username == "antonlacon":
							for i in range(0,bot_cfg.raffle_subscriber_entries):
								raffle_contestants.append(username)
								print("LOG: " + username + " is entry # " + str(len(raffle_contestants)))
						else:
							raffle_contestants.append(username)
							print("LOG: " + username + "is entry # " + str(len(raffle_contestants)))

				# Message monitor. Employ a strikeout system and ban policy.
				# Control with a True / False if language monitoring is active
				for language_control_test in language_watchlist.prohibited_words:
					if re.search(language_control_test, message): # and username not in privileged_users:

						add_user_strike(username)
						print ("LOG: " + username +" earned a strike for violating the language watchlist.")

						# Only need one violation per message, so stop searching when one is found
						break

				# Messages longer than a set length in all uppercase count as a strike
				if len(message) >= bot_cfg.uppercase_message_suppress_length and message == message.upper():
					add_user_strike(username)
					print ("LOG: " + username + " earned a timeout for a message in all capitals. Strike added.")

			# Drop messages of users PARTing, the user status messages in the specific channel (USERSTATE), the bot's GLOBALUSERSTATE, and users JOINing the channel
			elif re.search(r" PART ", message_line) or \
			re.search(r" USERSTATE ", message_line) or \
			re.search(r" GLOBALUSERSTATE", message_line) or \
			re.search(r" JOIN ", message_line):
				break

			# Not a channel message covered elsewhere
			else:
				print(message_line)

			# Rate control on sending messages
			sleep((1 / bot_cfg.rate) * messages_sent)

	except socket.error:
		print("ERROR: Socket died")

	except socket.timeout:
		print("ERROR: Socket timeout")

#if __name__ == "__main__":
# build loop into a function

# Loop broken; time to exit.
exit(0)
