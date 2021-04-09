# Planetside Open Games bot

![node](logos/bot.png) 

This repository contains POG bot, a discord bot used by [Planetside Open Games](https://docs.google.com/document/d/13rsrWA4r16gpB-F3gvx5HWf2T974mdHLraPSjh5DO1Q) to provide a community-driven matchmaking system for 6v6 infantry scrims in Planetside2.

### Requirements:
- This project relies on several [python dependencies](#python-dependencies).
- A [discord bot application and channels](#discord-bot-component) have to be created.
- A [MongoDB database](#preparing-mongodb-component) is used for persistent data storage. 
- Jaeger accounts are pulled from a [Google Sheet](#preparing-google-component). 
- To retrieve Planetside2 information a [Daybreak Census ID](#assigning-census-id) has to be provided.
- To use the TeamSpeak 3 Integration, set up an instance of [TS3AudioBot](#teamspeak-integration).
- Finally, to initialize the application, [scripts functions](#populating-the-collections) are provided.

### Python dependencies:
- Python 3.6 or above is required to run the project.
- We recommend using [pipenv](https://pypi.org/project/pipenv/) to set up the project environment. Pipenv will install automatically install the required dependencies from the `Pipfile` provided with the project.
- Alternatively, the dependencies are also listed in the `requirements.txt` file (compatible with [venv](https://docs.python.org/3/library/venv.html))

### Notes for the developer:
- Master branch is a release branch, it will stay clean and is synced with the official POG hosting server.
- So developments should be done on feature or development branches and will be then merged in.
- Keep fork repos up to date from upstream as much as possible.
- `google_api_secret.json` and `config.cfg` are not available for confidentiality reasons, templates are given instead.
- The code of the application itself can be found in the `bot` folder. It contains:
  - The `cogs` folder: it holds cogs modules as described in discord.py. Each of them regroups a set of commands and their associated checks. These modules are not to be imported in any way (they are only launched through the discord.py client)
  - The `display` folder: it is a python package handling all the display from the application to discord. All discords embed and strings used are stored there.
  - The `modules` folder: it is a python package containing general interfaces and tools that can be used in the rest of the application.
  - The `classes` folder: it contains the main classes of the application: `Player`, `Team`, `Weapon`, `Base`, `Account`, etc...
  - The `lib` folder: it contains third-party modules that were modified for the purpose of the application.
  - The `match` folder: it contains all the code handling the match processes and commands.
  
### Discord Bot Component
Create a bot application following the [discord.py documentation](https://discordpy.readthedocs.io/en/latest/discord.html).
The client-secret retrieved at this manual has to put into the configuration file:
```buildoutcfg
[General]
token = RetrievedDiscordApiBotToken
```

#### Create channels and roles
To retrieve discord channel, message and role-ids you have to enable Discord Developer Mode which can be toggled at appearance.
`Copy ID` will then appear at the right click menu for channels, messages and roles.
At that point you can populate the `[channels]` and `[roles]`sections of the configuration file.

### Preparing MongoDB Component
Pymongo is used for interaction with the mongodb. The database should contain several collections:
- One for the user data.
- One for the bases.
- One for the weapons.
- One for the matches.
- One for the player stats
- One for persistent restart data
- One for jaeger account usage
Check `script.py` to populate the databases.
The naming of these collections can be configured at the `[Collections]` part of the configuration file.

There are two common ways to get MongoDB running: [Atlas](#Atlas) and [Manual Deployment](#manual-deployment).

#### Atlas
Atlas can be run using a free instance at [MongoDB Cloud Atlas](https://www.mongodb.com/cloud/atlas)
When using MongoDB Atlas the following URI format is expected:
```buildoutcfg
[Database]
url = mongodb+srv://username:password@clusteruri/databasename
cluster = ClusterName
```

#### Manual Deployment
When using a single manually deployed MongoDB instance, omit `+srv` and remove the database name from the `url` and put it at `cluster` instead:
```buildoutcfg
[Database]
url = mongodb://username:password@host:port/
cluster = DatabaseName
```

### Preparing Google Component
The Gspread module is used for interaction with google API. [Follow these steps to create your google_api_secret.json](https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account)

#### Prepare Google Sheet
An example sheet has been provided called `accounts_sheet_template.xlsx`. 
By creating a new Google Sheet in your Drive and importing the excel file through the menu you can avoid format and naming convention errors.

The `accounts` field from the `[Database]` section of the configuration file has to contain the ID of the Google Sheet.
This ID can be easily retrieved from the URI of the document: `https://docs.google.com/spreadsheets/d/GOOGLE_SHEET_ID/edit#gid=0`.

Finally, add the service account email to the shared users with editor permissions to the google sheet. 
This email is also listed as `client_email` in the `google_api_secret.json` file.

### Assigning Census ID
Communication with the Daybreak Census API is required to retrieve game information, therefore you have to supply a Service ID.
You can apply for one at the [Daybreak Census](http://census.daybreakgames.com/#service-id) website.
Once you obtained an ID, add it the configuration as `api_key`:
```buildoutcfg
[General]
api_key = Daybreak_Registered_Service_ID
```

### Teamspeak integration
The bot used for Teamspeak audio integration is Splamy's [TS3AudioBot](https://github.com/yakMM/TS3AudioBot).
This bot works on the dotnet runtime and can be built and installed following the readme available in TS3AudioBot github's repo.
As of now, a fork of version `0.12.1` is used.

#### TS3-bot folder structure
The structure of the TS3AudioBot folder is the following:
```
TS3-bot
+-- TS3AudioBot.dll
+-- rights.toml
+-- ts3audiobot.toml
+-- ...
+-- audio
|   +-- audio_file_1.mp3
|   +-- audio_file_1.mp3
|   +-- ...
+-- bots
|   +-- 1
|   | +-- bot.toml
|   +-- 2
|   | +-- bot.toml
|   +-- 3
|   | +-- bot.toml
|   +-- ...
```
The audio files should be put in the `audio` repository. Each sub-repository of `bots` represent TS3 bot (one bot per match channel is needed).

#### Main configuration file
The first file to modify is `ts3audiobot.toml`. The relevant parameters for are listed below. You may want to change the parameters depending on your project file structure.
```buildoutcfg
[configs]
# Path for the bots
bots_path = "bots"

[factories]
# Path for audio files
media = { path = "audio" }

[bot.audio]
# Activate subscription-based whispers
send_mode = "!whisper subscription"


[bot.connect]
# TS3 default connect information
address = Your_TS3_Url
channel = Your_TS3_Bot_Channel_Id (example: /10)
```

Additionally, add access to all commands for localhost in the `rights.toml` file:
```buildoutcfg
# Admin rule
[[rule]]
        # Treat requests from localhost as admin
        ip = [ "::ffff:127.0.0.1" ]
        "+" = "*"
```

#### Configuring individual bots
Each individual bot can also be configured, in each `bot.toml` files. This allows for example to change the name of each individual bot.
```buildoutcfg
[connect]
# Client nickname when connecting.
name = "POG_3"

```

#### Setting up TS3 channels IDs
THe channel IDs can be set up in the configuration file: 




### Populating the collections
The file `scripts.py` contains two functions called `push_accounts()` and `get_all_maps_from_api()`.
The file `weapons_script.py` contains the function `push_all_weapons()`.
Running all of these functions will populate the MongoDB users, bases and weapons collections, allowing you to run `main.py`.
