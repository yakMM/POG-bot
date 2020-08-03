# Planetside Open Games bot

<img src="logos/bot.png" width="200">

@TODO: write a proper README

@TODO: write proper doc in the code

### Storage:

- The app uses a mongoDB database. Pymongo is used for interaction with the mongodb. As of now, the database should contain two collections: one for the bases and one for the user data. Check `script.py` to populate the databases.
- Jaeger accounts are stored in a google sheet spreadsheet. Gspread module is used for interaction with google API. [Follow these steps to create your client_secret.json](https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account)

### Notes for the developper:

- Master branch is a release branch, it will stay clean and is synched with the hosting.
- So developments should be done on feature branches and will be then merged in.
- Keep fork repos up to date from upstream as much as possible.
- `client_secret.json` and `config.cfg` are not available for confidentiality reasons, templates are given instead.
- `cogs` folder contains cogs modules as descibed in discord.py. Each of them regroups a set of commands and their associated checks. The core functionalities/processes are in `classes` folder.
    - These modules are not to be imported in any way (they are only launched through the discord.py client)
    - As such, it's not a problem to import anything from the `cogs`
- `modules` folder contains interfaces to the outside of the programm and tools susceptible to be used by the program.
    - These modules are to be imported when needed.
    - Do not import any of the `classes` modules from here, this would most likely lead to circular importation and reveal a bad design choice
- `classes` folder contains all the main processes, the core of the application its classes.
    - Only `modules` modules and external modules can be imported from here.
    - Do not import any of the `classes` modules from here.

