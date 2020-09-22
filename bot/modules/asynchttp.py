"""Handle asynchronous http requests to Census API

Usage:
    * jsonResultFile = await request(url)
"""

# Others
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientOSError, ClientConnectorError
from json import loads
from logging import getLogger

# Custom modules
from modules.exceptions import UnexpectedError, ApiNotReachable

log = getLogger(__name__)

# PUBLIC:

async def request(url):
    async with ClientSession() as client:
        result = await _fetch(client, url)
        return loads(result)

async def apiRequestAndRetry(url):
    for i in range(5):
        try:
            jdata = await request(url)
        except (ClientOSError, ClientConnectorError):
            log.warn(f"ClientError on try {i} for {url}")
            continue  # Try again
        if "returned" in jdata:
            return jdata
        else:
            log.warn(f"Nothing returned on try {i} for {url}")
    raise ApiNotReachable(url)

# PRIVATE:

async def _fetch(client, url):
    async with client.get(url) as resp:
        if resp.status != 200:
            raise UnexpectedError("Received wrong status from http page: " + str(resp.status))
        return await resp.text()
