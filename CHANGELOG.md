# v3.0:
- Match process rewrite [IN PROGRESS]
- Changed how demote works:
  - It's only possible to demote/resign a captain when it's their turn
  - On resign, player is not put back in the picking pool but instead added to the team as a player
  - It is now possible to demote/resign even after picking players
- Streamlined sub process
  - Captains can now be substituted, a new captain will automatically get chosen
  - It is now possible to sub players at any time before match start
- Changed base selection:
  - Bases are now selected with =base (=b) command
  - Current base can now be modified at any time before match start by team captains (even before players are picked)
- match command (=m) replaced by info command (=i)
- =p or =p help will now give info on the picking progress instead of displaying generic command help
- Code cleaning/commenting/documenting


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
