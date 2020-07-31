# Planetside Open Matches bot

@TODO: write a proper README

@TODO: write proper doc in the code

### Notes on the project's structure:

- Master branch is a realase branch, it will stay clean and is synched with the hosting.
- Developments should be done in side branches and will be then merged in
- `client_secret.json` and `config.cfg` are not available for confidentiality reasons, templates are given instead
- `cogs` folder contains cogs modules as descibed in discord.py. Each of them regroups a set of commands and their associated checks. The core functionalities/processes are in `classes` folder.
    - These modules are not to be imported in any way (they are only launched through the discord.py client)
    - As such, it's not a problem to import anything from the `cogs`
- `modules` folder contains interfaces to the outside of the programm and tools susceptible to be used by the program.
    - These modules are to be imported when needed.
    - Do not import any of the `classes` modules from here, this would most likely lead to circular importation and reveal a bad design choice
- `classes` folder contains all the main processes, the core of the application its classes.
    - Only `modules` modules and external modules can be imported from here.
    - Do not import any of the `classes` modules from here.

