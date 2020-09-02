"""Handle asynchronous http requests to Census API

Usage:
    * jsonResultFile = await request(url)
"""

# Others
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientOSError
from json import loads

# Custom modules
from modules.exceptions import UnexpectedError, ApiNotReachable


# PUBLIC:

async def request(url):
    async with ClientSession() as client:
        try:
            result = await _fetch(client, url)
        except ClientOSError:
            raise ApiNotReachable(url)
        return loads(result)


# PRIVATE:

async def _fetch(client, url):
    async with client.get(url) as resp:
        if(resp.status != 200):
            raise UnexpectedError("Received wrong status from http page: "+str(resp.status))
        return await resp.text()
