# Planetside Open Games bot

<img src="logos/bot.png" width="200">

@TODO: write a proper README

@TODO: write proper doc in the code

### Requirements:
- This project uses a `requirements.txt` to relay its dependencies that need to be installed.
- A [discord bot application and channels](#discord-bot-component) have to be created.
- The app uses a [MongoDB database](#preparing-mongodb-component). 
- Jaeger accounts are managed from a [Google Sheet](#preparing-google-component). 
- To retrieve PS2 game information a [Daybreak Census ID](#assigning-census-id) has to be provided.
- Finally, to prepare the environment, [two `script.py` functions](#populating-the-collections) have to be run.


### Notes for the developer:

- Master branch is a release branch, it will stay clean and is synced with the hosting.
- So developments should be done on feature branches and will be then merged in.
- Keep fork repos up to date from upstream as much as possible.
- `client_secret.json` and `config.cfg` are not available for confidentiality reasons, templates are given instead.
- `cogs` folder contains cogs modules as described in discord.py. Each of them regroups a set of commands and their associated checks. The core functionalities/processes are in `classes` folder.
    - These modules are not to be imported in any way (they are only launched through the discord.py client)
    - As such, it's not a problem to import anything from the `cogs`
- `modules` folder contains interfaces to the outside of the program and tools susceptible to be used by the program.
    - These modules are to be imported when needed.
    - Do not import any of the `classes` modules from here, this would most likely lead to circular importation and reveal a bad design choice
- `classes` folder contains all the main processes, the core of the application its classes.
    - Only `modules` modules and external modules can be imported from here.
    - Do not import any of the `classes` modules from here.    
    
    
#### Discord Bot Component
Create a bot application following the [discord.py documentation](https://discordpy.readthedocs.io/en/latest/discord.html).
The client-secret retrieved at this manual has to put into the configuration at:
```buildoutcfg
[General]
token = RetrievedDiscordApiBotToken
```

##### Create channels and roles
To retrieve discord channel, message and role-ids you have to enable Discord Developer Mode which can be toggled at appearance.
`Copy ID` will then appear at the right click menu for channels, messages and roles.
At that point you can populate the `[Discord_Ids]` section of the configuration.

#### Preparing MongoDB Component
Pymongo is used for interaction with the mongodb. As of now, the database should contain two collections: one for the bases and one for the user data. Check `script.py` to populate the databases.
The mapping of these can be configured at the `[Collections]` part of the config.

There are two common ways to get MongoDB running: [Atlas](#Atlas) and [Manual Deployment](#manual-deployment).

##### Atlas
Atlas can be run using a free instance at [MongoDB Cloud Atlas](https://www.mongodb.com/cloud/atlas)
When using MongoDB Atlas the following URI format is expected:
```buildoutcfg
[Database]
url = mongodb+srv://username:password@clusteruri/databasename
cluster = ClusterName
```

##### Manual Deployment
When using a single manually deployed MongoDB instance, omit `+srv` and remove the database name from the `url` and put it at `cluster` instead:
```buildoutcfg
[Database]
url = mongodb://username:password@host:port/
cluster = DatabaseName
```

#### Preparing Google Component
The Gspread module is used for interaction with google API. [Follow these steps to create your client_secret.json](https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account)

##### Prepare Google Sheet
An example excel sheet has been provided called `pug-accounts.xlsx`. 
By creating a new Google Sheet in your Drive and importing the excel file through the menu you can avoid format and naming convention errors.

The `accounts` configuration at `[Database]` has to contain the ID of the Google Sheet.
This ID can be easily retrieved from the URI of the document: `https://docs.google.com/spreadsheets/d/GOOGLE_SHEET_ID/edit#gid=0`.

Finally, add the service account email to the shared users with editor permissions to the google sheet. 
This email is also listed as `client_email` at the `client_secret.json`.

#### Assigning Census ID
Communication with the Daybreak Census API is required to retrieve game information, therefore you have to supply a Service ID.
You can apply for one at the [Daybreak Census](http://census.daybreakgames.com/#service-id) website.
Once you obtained an ID, add it the configuration as `api_key`:
```buildoutcfg
[General]
api_key = Daybreak_Registered_Service_ID
```

#### Populating the collections
The file `scripts.py` contains two functions called `pushAccounts()` and `getAllMapsFromApi()`. 
Running both of these functions will populate the MongoDB users and bases collections, allowing you to run `main.py`.
