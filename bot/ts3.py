import requests


class Ts3_bot:
    def __init__(self, main_url, username="admin", password=""):
        self.main_url = main_url
        botID_endpoint = "/botId"
        self.botId = requests.get(self.main_url + botID_endpoint).json()["defaultBotId"]

        login_endpoint = '/login'
        data = {'username': username, 'password': password, 'botId': self.botId}
        self.auth_token = requests.post(self.main_url + login_endpoint, data=data).json()["token"]

        instances_endpoint = '/instances'
        response = requests.get(self.main_url + instances_endpoint, headers={"Authorization": "Bearer " + self.auth_token}).json()

        self.instanceId = None
        if response[0]["backend"] == "ts3":
            self.instanceId = response[0]["uuid"]
        elif response[1]["backend"] == "ts3":
            self.instanceId = response[1]["uuid"]
        assert self.instanceId

    def volume(self, value):
        endpoint = "/volume/set/"
        x = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + str(value),
                          headers={"Authorization": "Bearer " + self.auth_token})
        print(x.content)

    def get_list(self):
        endpoint = "/files"
        x = requests.get(self.main_url + endpoint,
                         headers={"Authorization": "Bearer " + self.auth_token}).json()
        for item in x:
            print(item)

    def play(self, songId):
        endpoint = "/play/byId/"
        x = requests.post(self.main_url + "/i/" + self.instanceId + endpoint + songId,
                         headers={"Authorization": "Bearer " + self.auth_token})
        print(x)


bot = Ts3_bot('http://127.0.0.1:8087/api/v1/bot', username='admin', password='pogbot',
              botId='264950fc-86ea-4e98-8cf1-b3fced4a4f2a')

# 'uuid': '76611abe-7c55-45cd-95a5-9e6ffb6a5328', '5s'}
# 'uuid': '7dc870ca-6168-400c-a0f7-f2e3810f5364', 'lobby_full'}
# 'uuid': '374e9146-40af-48d9-a605-fa4515aca4c4', 'title': 'map_selected'}
# 'uuid': 'c913dbff-96ba-43e3-a99b-825344b1f792', 'title': 'round_over'}
# 'uuid': 'f2cd8897-b6a3-4404-a7ad-bd44e99ab231', 'title': 'select_factions'}
# 'uuid': '9603f6c9-f2bd-4ccc-8f6e-e2adf8b395ac', 'title': 'select_teams'}
# 'uuid': 'd6b5fb2f-dce3-4c56-a2c4-0e9cec130cbe', 'title': 'type_ready'}
# 'uuid': 'e8b0dc18-602a-4e4e-9b08-f8f732bb1c07', 'title': '10s'}
# 'uuid': 'aea1b593-e447-4bd1-9196-36d14942e78f', 'title': '30s'}