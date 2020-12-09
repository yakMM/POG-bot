# @CHECK 2.0 features OK

"""Handle asynchronous http requests to Census API

Usage:
    * json_result_file = await request(url)
"""

# Others
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientOSError, ClientConnectorError
from json import loads
from logging import getLogger

# Custom modules
from modules.exceptions import UnexpectedError, ApiNotReachable

log = getLogger("pog_bot")

# PUBLIC:

async def request(url):
    async with ClientSession() as client:
        result = await _fetch(client, url)
        return loads(result)

async def request_code(url):
    async with ClientSession() as client:
        result = await _fetch_code(client, url)
        return result

async def api_request_and_retry(url):
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

async def _fetch_code(client, url):
    async with client.get(url) as resp:
        return resp.status
