import logging
import requests
import json


# audio files use https://www.naturalreaders.com/online/ English (UK) - Amy voice

# because we only have 2 bots that jump around, make sure matches don't start within 10 seconds of each other so the
#  bot has time to move.

# settings to enable when bot instance is configured: enable the webapi script, insert teamspeak address and port, set
#  default channel (Lobby or Match 2 for each bot), set nickname.


class Ts3_bot:
    def __init__(self, main_url, instance_name, username="admin", password=""):
        self.initialized = None

        if main_url and instance_name:
            self.main_url = main_url
            botID_endpoint = "Id"
            self.botId = requests.get(self.main_url + botID_endpoint).json()["defaultBotId"]

            login_endpoint = '/login'
            data = {'username': username, 'password': password, 'botId': self.botId}
            self.auth_token = requests.post(self.main_url + login_endpoint, data=data).json()["token"]

            instances_endpoint = '/instances'
            response = requests.get(self.main_url + instances_endpoint,
                                    headers={"Authorization": "Bearer " + self.auth_token}).json()

            self.instanceId = None
            try:
                for instance in response:
                    if instance["name"] == instance_name:
                        self.instanceId = instance["uuid"]
                assert self.instanceId
                self.initialized = True
            except AssertionError as ae:
                logging.error(f"Assertion Error. Instance ID not returned.\n{ae}")

    def enqueue(self, songId):
        # enqueue will wait for the previous audio file to finish playing.
        # must wait >1 second between enqueues due to a sinusbot bug
        if self.initialized:
            endpoint = "/queue/append/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def get_list(self):
        if self.initialized:
            endpoint = "/files"
            response = requests.get(self.main_url + endpoint,
                                    headers={"Authorization": "Bearer " + self.auth_token}).json()
            tracks = []
            for track in response:
                tracks.append((track['uuid'], track['title']))
            return tracks
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def move(self, channelId, channelPass=""):
        if self.initialized:
            endpoint = "/event/move"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token,
                                              'Content-Type': 'application/json'},
                                     data=json.dumps({"id": channelId, "password": channelPass}))
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def play(self, songId):  # play will cut off any audio file currently playing
        if self.initialized:
            endpoint = "/play/byId/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def restart(self):
        if self.initialized:
            endpoint = "/respawn"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def shutdown(self):
        if self.initialized:
            endpoint = "/kill"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def spawn(self):
        if self.initialized:
            endpoint = "/spawn"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def stop_song(self):
        if self.initialized:
            endpoint = "/stop"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def volume(self, value):
        if self.initialized:
            endpoint = "/volume/set/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + str(value),
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")

    def get_queue(self):
        if self.initialized:
            endpoint = "/queue"
            response = requests.get(self.main_url + "/i/" + self.instanceId + endpoint,
                                    headers={"Authorization": "Bearer " + self.auth_token})
            return response.content
        else:
            logging.warning("Error: unable to complete request, ts3 bot not initialized")


def init():
    logging.basicConfig(level="INFO")

    try:
        global bot1, bot2
        bot1 = Ts3_bot(None, None)
        bot2 = Ts3_bot(None, None)
        bot1 = Ts3_bot('http://x127.0.0.1:8087/api/v1/bot', "bot1", username='admin', password='pogbot')
        bot2 = Ts3_bot('http://x127.0.0.1:8087/api/v1/bot', "bot2", username='admin', password='pogbot')

        if bot1.initialized and bot2.initialized:
            logging.info("TS3 bots are online")
        else:
            raise ConnectionError

    except ConnectionError as ce:
        logging.warning(f"Unable to initialize TS3 bots!\n{ce}")
    except Exception as e:
        logging.error(f"Uncaught exception starting ts3 bots! Unable to initialize TS3 bots: {type(e).__name__}\n{e}")
