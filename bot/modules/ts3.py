import logging
import requests
import json
from logging import getLogger
import modules.config as cfg

log = getLogger(__name__)


# audio files use https://www.naturalreaders.com/online/ English (UK) - Amy voice

# because we only have 2 bots that jump around, make sure matches don't start within 10 seconds of each other so the
#  bot has time to move.

# settings to enable when bot instance is configured: enable the webapi script, insert teamspeak address and port, set
#  default channel (Lobby or Match 2 for each bot), set nickname.


class Ts3Bot:
    class WebapiError(Exception):
        pass

    class SinusbotAuthError(Exception):
        pass

    def __init__(self, main_url, instance_name, username="admin", password=""):
        self.initialized = None

        if main_url and instance_name:
            self.main_url = main_url
            botID_endpoint = "Id"
            self.botId = requests.get(self.main_url + botID_endpoint).json()["defaultBotId"]

            login_endpoint = '/login'
            data = {'username': username, 'password': password, 'botId': self.botId}
            self.auth_token = ""
            try:
                login_response = requests.post(self.main_url + login_endpoint, data=data)
                if login_response.status_code == 401:
                    raise self.SinusbotAuthError
                else:
                    self.auth_token = login_response.json()["token"]
            except self.SinusbotAuthError as sae:
                log.error(f"Bad sinusbot username or password. Unable to connect.\n{sae}")

            instances_endpoint = '/instances'
            instances_response = requests.get(self.main_url + instances_endpoint,
                                              headers={"Authorization": "Bearer " + self.auth_token}).json()

            self.instanceId = None
            try:
                for instance in instances_response:
                    if instance["name"] == instance_name:
                        self.instanceId = instance["uuid"]
                assert self.instanceId
                self.initialized = True
            except AssertionError as ae:
                log.error(f"Assertion Error. Instance ID not returned.\n{ae}")

            # load song ids and durations into memory
            songlist_endpoint = "/files"
            songlist_response = requests.get(self.main_url + songlist_endpoint,
                                             headers={"Authorization": "Bearer " + self.auth_token}).json()
            self.track_durations = {}
            for track in songlist_response:
                if track['uuid'] in cfg.audio_ids.values():
                    self.track_durations[track['uuid']] = track['duration']
                    log.debug(track['uuid'], str(track['duration']))

    def check_initialized(self):
        if self.initialized:
            return True
        else:
            log.warning(f"Unable to complete request. TS3 bot not initialized.")
            return False

    def enqueue(self, songId):
        # enqueue will wait for the previous audio file to finish playing.
        # must wait >0.1 second between enqueues due to a sinusbot bug
        if self.check_initialized():
            endpoint = "/queue/append/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def get_duration(self, songId):
        if self.check_initialized():
            pad = 400  # extra time in ms to extend past duration
            try:
                return (self.track_durations[songId] + pad)/1000
            except KeyError:
                logging.warning("Track uuid does not exist!")
                return 0
        else:
            return 0

    def get_list(self):
        if self.check_initialized():
            endpoint = "/files"
            response = requests.get(self.main_url + endpoint,
                                    headers={"Authorization": "Bearer " + self.auth_token}).json()
            tracks = []
            for track in response:
                tracks.append((track['uuid'], track['title'], track['duration']))
            return tracks

    def move(self, channelId, channelPass=""):
        if self.check_initialized():
            endpoint = "/event/move"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token,
                                              'Content-Type': 'application/json'},
                                     data=json.dumps({"id": channelId, "password": channelPass}))
            return response

    def play(self, songId):  # play will cut off any audio file currently playing
        if self.check_initialized():
            endpoint = "/play/byId/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def restart(self):
        if self.check_initialized():
            endpoint = "/respawn"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def shutdown(self):
        if self.check_initialized():
            endpoint = "/kill"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def spawn(self):
        if self.check_initialized():
            endpoint = "/spawn"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def stop_song(self):
        if self.check_initialized():
            endpoint = "/stop"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def volume(self, value):
        if self.check_initialized():
            endpoint = "/volume/set/"
            response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + str(value),
                                     headers={"Authorization": "Bearer " + self.auth_token})
            return response

    def get_queue(self):
        if self.check_initialized():
            endpoint = "/queue"
            response = requests.get(self.main_url + "/i/" + self.instanceId + endpoint,
                                    headers={"Authorization": "Bearer " + self.auth_token})
            return response.content


def init():
    try:
        bot1 = Ts3Bot('http://localhost:8087/api/v1/bot', "bot1",
                      username=cfg.general["sinusbot_user"], password=cfg.general["sinusbot_pass"])
        bot2 = Ts3Bot('http://localhost:8087/api/v1/bot', "bot2",
                      username=cfg.general["sinusbot_user"], password=cfg.general["sinusbot_pass"])

        if bot1.initialized and bot2.initialized:
            # test if webapi.js extension is enabled by moving bots to a nonexistent channel and checking http response
            if bot1.move("").status_code != 500 and bot2.move("").status_code != 500:
                log.info("TS3 bots are online")
            else:
                bot1.initialized = False
                bot2.initialized = False
                raise Ts3Bot.WebapiError
        else:
            raise ConnectionError
    except ConnectionError as ce:
        log.warning(f"Unable to initialize TS3 bots! Continuing script without bots functioning...\n{ce}")
    except Ts3Bot.WebapiError as we:
        log.warning(f"Unable to send 'move' command to TS3 bots! Is the webapi extension enabled for Sinusbot? "
                    f"Continuing script without bots functioning...\n{we}")
    except Exception as e:
        log.error(f"Uncaught exception starting ts3 bots! Continuing script without bots functioning... {type(e).__name__}\n{e}")


# FOR TESTING:
if __name__ == "__main__":
    cfg.getConfig(f"config{''}.cfg")
    init()
