from time import sleep

import requests
import json


# audio files use https://www.naturalreaders.com/online/ English (UK) - Amy voice

# because we only have 2 bots that jump around, make sure matches don't start within 10 seconds of each other so the
#  bot has time to move.

# settings to enable when bot instance is configured: enable the webapi script, insert teamspeak address and port, set
#  default channel (Lobby or Match 2 for each bot), set nickname.


class Ts3_bot:
    def __init__(self, main_url, instance_name, username="admin", password=""):
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
        for instance in response:
            if instance["name"] == instance_name:
                self.instanceId = instance["uuid"]
        assert self.instanceId

    def enqueue(self,
                songId):  # enqueue will wait for the previous audio file to finish playing. must wait >1 second between enqueues due to a sinusbot bug
        endpoint = "/queue/append/"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def get_list(self):
        endpoint = "/files"
        response = requests.get(self.main_url + endpoint, headers={"Authorization": "Bearer " + self.auth_token}).json()
        tracks = []
        for track in response:
            tracks.append((track['uuid'], track['title']))
        return tracks

    def move(self, channelId, channelPass=""):
        endpoint = "/event/move"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                 headers={"Authorization": "Bearer " + self.auth_token,
                                          'Content-Type': 'application/json'},
                                 data=json.dumps({"id": channelId, "password": channelPass}))
        return response

    def play(self, songId):  # play will cut off any audio file currently playing
        endpoint = "/play/byId/"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def restart(self):
        endpoint = "/respawn"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def shutdown(self):
        endpoint = "/kill"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def spawn(self):
        endpoint = "/spawn"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def stop_song(self):
        endpoint = "/stop"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint,
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def volume(self, value):
        endpoint = "/volume/set/"
        response = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + str(value),
                                 headers={"Authorization": "Bearer " + self.auth_token})
        return response

    def get_queue(self):
        endpoint = "/queue"
        response = requests.get(self.main_url + "/i/" + self.instanceId + endpoint,
                                headers={"Authorization": "Bearer " + self.auth_token})
        return response.content


bot1 = Ts3_bot('http://127.0.0.1:8087/api/v1/bot', "Lobby_and_Team1", username='admin', password='pogbot')
bot2 = Ts3_bot('http://127.0.0.1:8087/api/v1/bot', "Team2", username='admin', password='pogbot')

# print(lobby_bot.get_list())
AUDIO_ID_ROUND_OVER = 'a0fbc373-13e7-4f14-81ec-47b40be7ab13'
AUDIO_ID_SELECT_FACTIONS = '91da596c-2494-4dbc-9c59-71f74f3b68cb'
AUDIO_ID_SELECT_MAP = '21bb87b5-5279-45fd-90a7-7c31b5e5199d'
AUDIO_ID_SELECT_TEAMS = '6eb6f5cc-99bd-4df6-9b59-bc85bd88ba7c'
AUDIO_ID_TEAM_1_NC = 'f667d6c6-fc9a-4026-9cf7-e32844638450'
AUDIO_ID_TEAM_1_TR = '6922780b-56bd-47b3-9f38-6c228604f7ae'
AUDIO_ID_TEAM_1_VS = 'c8d7202f-fb81-47d5-8785-3512ba0bf233'
AUDIO_ID_TEAM_2_NC = '228d61e2-f466-4c99-89c5-4b658adf828e'
AUDIO_ID_TEAM_2_TR = 'c0dd6cad-a32c-4b2a-b229-2f22eb1da202'
AUDIO_ID_TEAM_2_VS = '1ad7209e-6329-463e-9d40-6b3e3ab1174e'
AUDIO_ID_TYPE_READY = '23ee2e94-8628-4285-aeee-d07e95a2f2ee'
AUDIO_ID_5S = '83693496-a410-4602-80dd-9ed74ec0a2fe'
AUDIO_ID_10S = '2b68e6d3-6009-4662-a72e-9d9e2b84d67b'
AUDIO_ID_30S = 'ff4d8310-06cd-449f-8d8e-00dda43dc102'
AUDIO_ID_DROP_MATCH_1_PICKS = '663c62b8-5083-49d0-bed2-29ead13b749c'
AUDIO_ID_DROP_MATCH_2_PICKS = '540f93a5-9ccb-4cdc-8faf-4f3458625c80'
AUDIO_ID_GELOS_IN_PRISON = '1db0bb0d-d82c-41de-ad90-0403c69ad37c'
AUDIO_ID_MAP_SELECTED = 'ecf7b363-68dc-45d4-a69d-25553ce1f776'
AUDIO_ID_PLAYERS_DROP_CHANNEL = 'e67dc6a7-2731-419f-a179-6c4614189ab0'
# todo: put these in a config file

# bot.move("<CHANNEL ID>")
# PSB teamspeak channel ids:
# ts_lobby = "281"
# ts_afk = "282"
# ts_match_1_picks = "286"
# ts_match_1_team_1 = "284"
# ts_match_1_team_2 = "285"
# ts_match_2_picks = "323"
# ts_match_2_team_1 = "324"
# ts_match_2_team_2 = "325"

# todo: put these in a config file
