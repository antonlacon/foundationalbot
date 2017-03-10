#!/usr/bin/env python3
# Copyright 2016 Ian Leonard <antonlacon@gmail.com>
#
# This file is fb_sql.py and is part of the Foundational IRC Bot for
# Twitch.tv project.
#
# fb_sql.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# fb_sql.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with fb_sql.py. If not, see <http://www.gnu.org/licenses/>.

""" TODO:
	Split table creation into one that includes channel data(?)
	Add limit to searches / queries / inserts where channel is taken into account
	Add a maintenance action where user is deleted from table if strikecount meets limit
	Teach argument parameters for calling directly:
		Wipe viewer currency
		Wipe raffle status
		Reset all tables
		verbose debug info(?)
		Reindex & Vacuum
	Move the database cursor into config.py
"""

# Core Modules
import sqlite3
# argparse?
# Project Modules
import bot_cfg

### HELPER FUNCTIONS ###

### OPENING AND CLOSING CONNECTIONS ###

def db_initialize(db_name=':memory:'):
	""" Initalize connection to specific database and return connection info. """
	db_connection = sqlite3.connect( db_name )
	db_action = db_connection.cursor()

	return db_connection, db_action

def db_shutdown(db_connection):
	""" Commit any changes and close database connection. """
	db_connection.commit()
	db_connection.close()

### DATABASE ADDITIONS ###

def db_vt_createtable(db_action):
	""" Create the Viewer table that stores:
		Channel: Channel viewer is in
		Username: Username in Twitch's chat server
		DisplayName: Name displayed by user in chat
		Strikes: Internal counter for user's strikes in timeout/ban system
		Currency: Internal counter for user's time spent in channel
		Raffle: Raffle participant
	"""
	# use IF NOT EXISTS to avoid having to test if table exists before creation
	db_action.execute( '''CREATE TABLE IF NOT EXISTS Viewers(
		Username TEXT PRIMARY KEY,
		DisplayName TEXT,
		Strikes INTEGER DEFAULT 0,
		Currency INTEGER DEFAULT 0,
		Raffle INTEGER DEFAULT 0)
		WITHOUT ROWID''' )

def db_vt_addentry(db_action, user, displayname=None):
	""" Add a new row to the Viewers table. """
	# TODO: able to mix default and non-default values?
	db_action.execute( "INSERT INTO Viewers VALUES (?,?,0,0,0)", (user, displayname) )

### DB QUERIES ###
def db_vt_test_username(db_action, key_value):
	""" Query viewer's username to see if present in table. Returns true/false. """
	query_result = db_action.execute( "SELECT Username FROM Viewers WHERE Username = ?", (key_value,)).fetchall()
	if len( query_result ) > 0:
		return True
	else:
		return False

def db_vt_show_all(db_action):
	""" Query and return the entire Viewers table. """
	query_result = db_action.execute( "SELECT * FROM Viewers").fetchall()

	return query_result

def db_vt_show_all_raffle(db_action):
	""" Query all raffle participants. """
	query_result = db_action.execute( "SELECT Username FROM Viewers WHERE Raffle = 1").fetchall()

	return query_result

def db_vt_show_displayname(db_action, key_value):
	""" Query viewer's chat display name and return it. """
	query_result = db_action.execute( "SELECT DisplayName FROM Viewers WHERE Username = ?", (key_value,)).fetchall()

	return query_result[0][0]

def db_vt_show_strikes(db_action, key_value):
	""" Query viewer's current strike count and return it. """
	query_result = db_action.execute( "SELECT Strikes FROM Viewers WHERE Username = ?", (key_value,)).fetchall()

	return query_result[0][0]

def db_vt_show_currency(db_action, key_value):
	""" Query viewer's current amount of currency and return it. """
	query_result = db_action.execute( "SELECT Currency FROM Viewers WHERE Username = ?", (key_value,)).fetchall()

	return query_result[0][0]

def db_vt_show_raffle(db_action, key_value):
	""" Query viewer's participation in a raffle. """
	query_result = db_action.execute( "SELECT Raffle FROM Viewers WHERE Username = ?", (key_value,)).fetchall()

	if query_result[0][0] == 0:
		return False
	elif query_result[0][0] == 1:
		return True

### CHANGING DB VALUES ###

def db_vt_delete_user(db_action, key_value):
	""" Delete a row from the Viewers' table """
	db_action.execute( "DELETE FROM Viewers WHERE Username = ?", (key_value,))

def db_vt_change_displayname(db_action, key_value, update_value):
	""" Update a user's DisplayName. """
	# if WHERE fails to match any rows, then no rows are updated - does not error
	db_action.execute( "UPDATE 'Viewers' SET DisplayName = ? WHERE Username = ?", (update_value, key_value,) )

def db_vt_change_strikes(db_action, key_value, strike_value):
	""" Change strike count of specified user. """
	# Update database strike count
	db_action.execute( "UPDATE Viewers SET Strikes = ? WHERE Username = ?", (strike_value, key_value,))

def db_vt_change_currency(db_action, key_value, increase_amount):
	""" Increase a user's currency by the specified value. """
	currency_count = db_vt_show_currency(db_action, key_value) + increase_amount

	# Update database currency value
	db_action.execute( "UPDATE Viewers SET Currency = ? WHERE Username = ?", (currency_count, key_value))

def db_vt_change_raffle(db_action, key_value):
	""" Toggle a viewer's raffle participation status. """
	raffle_participation = db_vt_show_raffle(db_action, key_value)

	# flip current value to opposite (0 is false, 1 is true)
	if raffle_participation == False:
		db_action.execute( "UPDATE Viewers SET Raffle = 1 WHERE Username = ?", (key_value,))
	elif raffle_participation == True:
		db_action.execute( "UPDATE Viewers SET Raffle = 0 WHERE Username = ?", (key_value,))

### MAINTENANCE ACTIONS ###

def db_vt_resetallcurrency(db_action):
	""" Reset all viewers' currency to 0. """
	db_action.execute( "UPDATE Viewers SET Currency = 0" )

# TODO convert to generic table drop
def db_vt_resetviewers(db_action):
	""" Globally wipe the Viewer table data. """
	db_action.execute( "DROP TABLE IF EXISTS Viewers" )

def db_vt_reset_all_raffle(db_action):
	""" Reset all viewers' raffle participation. """
	db_action.execute( "UPDATE Viewers SET Raffle = 0" )

def db_vt_remove_banned_viewers(db_action):
	""" Remove viewers from table that reached the strikecount limit. """
	db_action.execute( "DELETE FROM Viewers WHERE Username = ? AND Strikes >= ?", (key_value, bot_cfg.strikes_until_ban,))

### MAIN ###
if __name__ == "__main__":
	print("Connection to database...")
	db_connection, db_action = db_initialize()

	print("Closing database connection...")
	db_shutdown(db_connection)
