# v3.3:
- Added stat processor module
- Added =psb command for usage tracking
- Changed the way DM messages are handled
- updated = timeout command
- It is now possible to use =swap and =sub between two rounds
- Added =bench / =unbench command
- Added doc folder
- Accounts are now added to player objects before validation

# v3.2:
- Added locking mechanic on reaction handler to avoid errors due to players spamming the reactions
- Overhauled the use of async functions for critical events
- Changed "Last played" to "Previously played"
- Players are now freed as soon as the match round ends
- =squittal can now be used when the match is starting
- =base can now be used when the match is starting
- Now displaying players in-game names in the match info embed
- Removed the base navigator as it was rarely used
- Players can now reset their lobby timeout with a reaction
- Bot now use only necessary gateway intents (discord API)
- Added proper logger Plugin
- Added embed showing player status when using =r command
- Added basic stats display

# v3.1:
- Fixed some issues with sub command
- Added base image as thumbnail in the match info embed
- Notify players will no longer be pinged if they are already in a match
- Overhauled team ready section:
  - Added reactions for the =ready command
  - =sub can no longer be used on a player whose team is ready
  - =swap can no longer be used it a team is ready
  - It's no longer possible to change the base if a team is ready
- Overhauled scoring system:
  - Classes will now be properly reported on the score sheet
  - Now tracking per-class stats internally
- Added match plugins
  - Added ts3 interaction as a plugin
  - Fixed some problems in the ts3 bot handling
  - TS3 channels ids are not in the config file
- Separated =lobby get from =lobby save
- Players name are now displayed in lobby lists

# v3.0:
- Code revamp:
  - Added a process system to handle the different match events
  - Added a command system to handle the match commands
  - Database changes
  - Reworked the architecture/location of python packages within the project
  - Improved display classes
  - Bugfixes
- Accounts:
  - Jaeger accounts can now be handed dynamically one by one
  - Account usage is no longer reported to the account sheet, but logged inside the mongo database
  - Account logging details are pulled from a google sheet. They can be updated dynamically with =reload command
  - Players can receive accounts even when they are in hte "getting ready" phase.
- TS3 bot:
  - Because PSB teamspeak server was down, removed the TS3 interaction (could not test)
  - Will be added back in a coming patch
- Players:
  - Added handling of player stats (nb of matches, nb of kills, deaths, net, score)
  - Nb of matches is used to find potential Team captains
  - Players can now be renamed with =rename command
- Lobby:
  - The command =lobby get now saves the lobby state in the db.
  - The last lobby state is automatically used to fill the lobby on restart
  - There is now a timeout for lobby joins: players will be warned after 2 hours and kicked after 2h10m
  - Added =reset command to reset lobby timeout
  - Players can now join the lobby even if their discord status is offline
  - Players are no longer kicked of the lobby after they go offline in discord
- Match result:
  - The two most used classes of each player within the match are now displayed in the scoreboard
  - The bot will no longer print the banned weapon message twice (was happening when the weapon was used in the first round)
- General:
  - It is now possible to use command directly with discord ID instead of mention. For example =p 75451215457875 instead of =p @pog will work
  - Match channels are now closed (not visible any more) when no match is active, to reduce channel clutter
- Match:
  - match command (=m) has been replaced by info command (=i)
  - The bot will send a DM to players when the lobby is filled and a match start
  - Captains are no longer automatically selected. Rather, a step was added in which players can volunteer to be captains.
    - Each minute, the bot will suggest new captains until some players accept the role
  - Removed =resign =demote commands
  - Sub command:  
    - =sub should now work in all situations, until a round actually start: It is now possible to sub players in the getting ready phase
    - Captains can now use the sub command. A successful sub will require both captains to confirm the action
    - Admins can directly sub players in. (Whereas when captains use sub, a player is automatically picked form the lobby)
  - Added =swap command
    - It requires both captain confirmation
    - Swap players form one team to the other
  - Added =base command
    - Captains can now select a base whenever they want, and change the base several times until the round actually start
    - The bot will show if a base is currently used in another pog match
  - =p command (with no argument) will now display the picking status
  - Added reaction systems:
    - Confirmation of action between captains
    - Faction selection
    - Captain selection
    - Overhauled base selection system with reactions
  - Match status is now displayed automatically and refreshed regularly to show the time remaining
  - Added =check command for admins to disable account validation check or online check
- Account usage: Changed the way admins can check for POG account usage (command instead of google sheet)
- Register: players can now remove their account while in a match in the Getting ready phase. They will be given an account by the bot

# v2.1:
- Ingame online check feature now reactivates after each match
- Added =as command for admins to impersonate players
- Any message sent to the bot in DM will be forwarded to staff
- Flagged all the flip PIL accounts and ask users to re-register
- Match won't get stuck if a user has locked their DMs anymore
- Fixed error on =resign command
- Speculative fix for error with score calculation
- Fixed error with ghost accounts

# v2.0:
Major feature implementations!
- Added jaeger calendar integration
- Added a warning if a chosen base is currently reserved in the jaeger calendar
- Added a proper reaction framework:
  - Improved base pool and base selection process with reactions
- Implemented a teamspeak bot:
  - Bot announces match start and end, and informs captains on steps during pre-match
- Various code viewability enhancements, PEP8 formatting, and typo fixes
- Updated discord.py library
- Fixed error handling in tasks
- Some database changes
- Overhauled logging
- Misc :)

# v1.15:
- Cap points are no longer counted in team netscore
- Updated score sheet visual
- Added author in all embeds as workaround for discord android app bug T900 (long enbeds on mobile)

# v1.14:
- Added sub command for staff
- Updated help embeds for all channels
- Banned weapon usage is now reported in both match and staff channels
- Match info now shows the remaining time for current round
- Added rdy as alias for the ready command
- Added global information prompt accessible with command info
- All scores are now posted in the result channel
- Matches are now stored in database
- Added squittal command

# v1.13:
- Added match score tracking (BETA)
- Fixed bug with display of scores
- Fixed bugs with calculation of score
- Match should not hang anymore in case of an error in score calculation
- Added a lobby restore command
- Api calls are now retried if they fail
- Factions can now be modified again before the match start
- Fixed account sending infinite loop by handling error if a player has its DMs closed
- Now checking if players are online in game before allowing match to start

# v1.12:
- Added timeout functionality for admins
- Modifications in how players are stored in database
- Bot is now active in all channels listed in the config file
- Fixed a bug with muted permissions
- Fixed a bug with some staff commands being usable in wrong channels
- Fixed a bug when removing players from lobby
- Bot no longer ignore commands sent from match channels
- Added command for team captains to resign
- Staff can now demote team captains

# v1.11:
- Commands are no longer usable during init
- Fixed a bug with @Notify being pinged after a match start
- Staff can now remove individual players from lobby
- Speculative fix for bot taking 5 whole minutes to start
- Players can now see the channels on joining back the discord server

# v1.10:
- All players will now have accurate roles depending on their status
- Notify role should now reflect more accurately players ready to queue
- Fixed a bug with afk players in queue
- Overhauled player status code
- Tweaked the conditions for the bot to ping @Notify
- Fixed a bug allowing the one captain to choose a base and confirm it
- Added default base pool: players can't choose any base in the game anymore

# v1.9:
- Updated Jaeger Calendar Link
- Current UTC time is now displayed along Jaeger Calendar link
- Speculative fix for "ghost" matches
- Bot will now ping @Notify when queue is almost full
- Added logging in file

# v1.8:
- Fixed string when registering with a character already registered
- Fixed roles issues when user would leave the server and come back
- PS2 API error when registering a character is now clearly handled
- Fixed lobby problems occuring when no match slot is available
- freeze/unfreeze command is now working as expected

# v1.7:
- =map command should now work in all situations
- Fixed match status message on faction selection
- Added possibility to freeze and unfreeze channels

# v1.6:
- Fixed critical bug in account distribution (every account could only be used 1 time)
- Match length is now 10 minutes
- ALL commands are now case insensitive (it was the case of only a few)
- Fixed a bug when lobby is stuck but a match spot becomes available
- "Round 2 is over" message is no longer displayed twice
- Staff can now properly cancel an ongoing match

# v1.5:
- Added =pog command for version checking and locking/unlocking the bot
- Now ignoring messages posted in wrong channels
- Added help regarding notify feature
- Added link to Jaeger Calendar

# v1.4:
- Fixed a bug when several matches are happening at the same time
- Customized discord.ext.tasks as lib.tasks to have better flexibility on tasks
- Various fixes

# v1.3:
- It is no longer possible to register with a character that is already registered
- Team captains can now select a base
- Added =confirm command for Team Captains to agree on a base
- Added role updates when agreeing with the rules
- Added notify feature
- Added =unregister @player to remove a player from the system (including db)

# v1.2:
- Now properly checking if player have no missing faction when registering with a Jaeger char
- Lobby size can now be modified from the config file
- Overhauled the mechanic removing afk players from lobby: Now players have to stay 15 minutes offline to be removed. If they come online within these 15 minutes, the timeout resets.
- Fixed incorrect match numeration
- Last player is now pinged when automatically assigned to a team
- Matches are now constituted of 2 rounds
- Round number is now displayed

# v1.1:
- Rules acceptance feature
- Registration of users with their Jaeger accounts, linked with ps2 api and a backend database
- One lobby, multi matches system
- Lobby size can be modified
- All parameters are in a config file easily editable
- Slight anti spam system (user must wait for their message to be processed before sending another one, especially with the long commands doing api calls for example)
- Several matches can happen at the same time
- Afk player are removed from lobby
- Captains selected at random temp
- Picking feature
- Faction picking feature
- Map is chosen at random within the PIL base pool temp
- Staff can change the base to any ps2 base (linked to ps2 api)
- Automatic handing of Jaeger accounts with precise tracking in a google sheet for good human visibility
- Ability for staff to clear a match anytime before it actually starts
- Each captain can toggle their "ready state"
- Match starts only when both teams are ready
