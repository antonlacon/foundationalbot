Foundational Twitch Chat Bot
======

A chat bot for use by Twitch broadcasters to aid in the production of their channels. It requires at least Python 3.6.

# Status
This bot is functional, but a work in progress.

# Chat Commands
## Administrator
* !exit or !quit: Shutdown the bot
* !reconnect: Order bot to close and reopen network connection (here for testing)

## Broadcaster
* !raffle: Commands to run a raffle, or otherwise pick a random participating member of chat
	* !raffle keyword string: Open the raffle and monitor viewers' chat messages for string to add them to the raffle drawing
	* !raffle clear: Reset the raffle to a blank state
	* !raffle count: Send a message to chat with the number of participants in the raffle
	* !raffle close: Stop monitoring viewers' chat messages for the raffle keyword
	* !raffle reopen: Continue monitoring viewers' chat messages for the raffle keyword
	* !raffle winner: Choose and remove a winner from the raffle pool so multiple drawings may be made at once without having one person win multiple drawings
* !voice username: Restore chat privileges to a banned or timedout viewer

## Editor
None implemented.

## Moderator
None implemented.

## Viewer
* Gaming with the broadcaster
	* !psn or !ps4: Send PSN name to chat
	* !steam: Send Steam name to chat
	* !xbl or !xb1: Send XBox Live name to chat
* !schedule: Send bot's current time and broadcaster's schedule for that day
* !time: Send the bot's current time to chat

# Chat Monitoring
## Strikeout System
The bot works on a strike out system leading up to an eventual ban when enough strikes are accrued. The necessary strikes are set by the bot administrator.
## ALL CAPS
Chat messages longer than a (configured) length in all capital letters will be suppressed. Each such message earns a strike.
## Webpage address shorteners / lengtheners
Viewers should know where the address they click on from other viewers is taking them. Prohibit messages that obfuscate those addresses. The administrator, broadcaster, moderators, and the bot are exempt from this.
