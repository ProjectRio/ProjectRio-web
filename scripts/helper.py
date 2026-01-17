import json
import requests
from pprint import pprint

COMMUNITY_JSON_PATH = "community.json"
TAG_JSON_PATH = "tags.json"
TAGSET_JSON_PATH = "tagset.json"
GAME_JSON_PATH = "game.json"
COMMUNITY_INVITE_JSON_PATH = "invite.json"
USER_GROUP_PATH = "user_group.json"

# BASE_URL = "https://api.projectrio.app"
BASE_URL = "http://127.0.0.1:5000" # When running the app locally

def respin_rio_key(email):
    response = requests.get(f"{BASE_URL}/request_new_rio_key/?email={email}")
    pprint(response)

def request_password_change(username_or_email):
    user = {'username_or_email': username_or_email}
    response = requests.post(f"{BASE_URL}/request_password_change", json=user)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def change_password(active_url, new_password):
    user = {'active_url': active_url, 'password': new_password}
    response = requests.post(f"{BASE_URL}/change_password", json=user)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def register(username, email, password):
    user = {'Username': username, 'Email': email, 'Password': password}
    response = requests.post(f"{BASE_URL}/register", json=user)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def login(username, email, password):
    user = {'Username': username, 'Email': email, 'Password': password}
    response = requests.post(f"{BASE_URL}/login", json=user)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def vld_jwt():
    response = requests.post(f"{BASE_URL}/validate_JWT")
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def add_user_to_group(name, group):
    user = {'username': name, 'group_name': group, 'rio_key': RIO_KEY}
    response = requests.post(f"{BASE_URL}/user_group/add_user", json=user)
    print(response.json())

def remove_user_from_group(name, group):
    user = {'username': name, 'group_name': group, 'rio_key': RIO_KEY}
    response = requests.post(f"{BASE_URL}/user_group/remove_user", json=user)
    print(response.json())

def create_user_group():
    user = {'group_name': 'BetaTester', 'daily_limit': 0, 'weekly_limit': 0, 'sponsor_limit': 0}
    user['Rio Key'] = RIO_KEY
    response = requests.post(f"{BASE_URL}/user_group/create", json=user)
    print(response.json())

def join_comm(rio_key, comm_name, url):
    user = {'Rio Key': rio_key}
    comm_name = comm_name
    active_url = url
    full_url = f"{BASE_URL}/community/join/{comm_name}/{active_url}"
    response = requests.post(full_url, json=user)

def join_comm_no_url(rio_key, comm_name):
    rio_key = rio_key
    user = {'rio_key': rio_key, 'community_name': comm_name}
    full_url = f"{BASE_URL}/community/join"
    response = requests.post(full_url, json=user)


def invite_to_comm():
    f = open(COMMUNITY_INVITE_JSON_PATH)
    invite_list_json = json.load(f)
    invite_list = invite_list_json['invite_list']
    comm_name = invite_list_json['community_name']
    payload = {'rio_key': RIO_KEY, 'community_name': comm_name, 'invite_list': invite_list}
    full_url = f"{BASE_URL}/community/invite"
    response = requests.post(full_url, json=payload)
    if (response.status_code == 200):
        pprint(response.json())

def create_community():
    f = open(COMMUNITY_JSON_PATH)
    community = json.load(f)
    community['rio_key'] = RIO_KEY

    response = requests.post(f"{BASE_URL}/community/create", json=community)
    pprint(response.json())

def manage_community():
    payload = {'rio_key': RIO_KEY, 'community_name': '',
               'user_list': [{'username': '', 'action': ''}]}

    response = requests.post(f"{BASE_URL}/community/manage", json=payload)
    pprint(response.json())

def create_tags():
    f = open(TAG_JSON_PATH)
    tags = json.load(f)
    pprint(tags)
    for tag in tags['Tags']:
        tag['Rio Key'] = RIO_KEY
        response = requests.post(f"{BASE_URL}/tag/create", json=tag)
        pprint(response.status_code)
        if (response.status_code == 200):
            pprint(response.json())


def create_tagset():
    f = open(TAGSET_JSON_PATH)
    tagset = json.load(f)
    tagset['rio_key'] = RIO_KEY
    response = requests.post(f"{BASE_URL}/tag_set/create", json=tagset)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def delete_tagset(tag_set_name):
    payload = {'name':tag_set_name}
    payload['rio_key'] = RIO_KEY
    response = requests.post(f"{BASE_URL}/tag_set/delete", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def delete_tagset_all(exclude_official):
    payload=dict()
    payload['rio_key'] = RIO_KEY
    payload['exclude_official'] = exclude_official
    response = requests.post(f"{BASE_URL}/tag_set/delete/all", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def create_comm_keys(comm_name):
    payload = {'community_name': comm_name, 'action': 'generate'}
    response = requests.post(f"{BASE_URL}/community/key", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def get_ladder(tag_set):
    payload = {'TagSet': tag_set}
    response = requests.post(f"{BASE_URL}/tag_set/ladder", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def get_tagsets():
    payload = {'Client': 'true', 'Active': 'true', 'combine_codes': True}
    response = requests.post(f"{BASE_URL}/tag_set/list", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def update_tagset():
    for x in []: # Update batch of tag_sets
        payload = {'tag_set_id': x}

        payload['rio_key'] = RIO_KEY
        response = requests.post(f"{BASE_URL}/tag_set/update", json=payload)
        pprint(response.status_code)
        if (response.status_code == 200):
            pprint(response.json())

def update_tag():
    tags = [
        {"tag_id": 38, #MFS 4.1
         "desc": "Allows users to override the fielder selection AI",
         "type": "Gecko Code",
         "gecko_code": "20678F8C 88061BD1\nC2678F8C 0000003D\n7C6E1B78 7C0802A6\n90010004 9421FF00\nBC610008 3D20802E\n6129BF97 3C808089\n6084269E A0840000\n2C04000F 40810178\n3C808089 60842973\n88840000 2C040003\n40800024 3C808089\n60842701 88840000\n2C040000 41820010\n2C040003 41820008\n48000144 3D008089\n61082898 A1080000\n88890000 71050010\n2C050010 4082000C\n38800000 98890000\n71050800 2C050800\n4082000C 38800001\n98890000 71050400\n2C050400 4082000C\n38800002 98890000\n71050020 2C050020\n4082000C 38800003\n98890000 2C040004\n408000DC 2C040000\n418200D4 2C040003\n4182000C 3884FFFF\n48000074 3CE08089\n60E70B38 39000008\n38A00000 38800000\n3CC08088 60C6F368\nC3870000 C3A60000\nFFDCE828 FFDEF02A\nFFC0F210 7F883C2E\nC3A60008 FF9CE828\nFF9CE02A FF80E210\nFFDEE02A 2C050000\n4182000C FC0AF040\n4180000C FD40F090\n7CA42B78 38A50001\n38C60268 2C050009\n4082FFB0 3CC08088\n60C6F53B 39000000\n1D280268 7CA930AE\n2C05000F 4082000C\n38A00002 7CA931AE\n39080001 2C080009\n4180FFE0 1CA40268\n38E0000F 7CE531AE\n3CC08089 60C62800\n98860001 98860007\n48000028 38800000\n98890000 B8610008\n80010104 38210100\n7C0803A6 7DC37378\n88061BD1 4800001C\nB8610008 80010104\n38210100 7C0803A6\n7DC37378 38000001\n60000000 00000000\nE2000001 00000000\n",
         "gecko_code_desc": "Y pitcher, X catcher, R closest to ball, 15 frame initial lockout. Original mod by PeacockSlayer, improved and perfected by [LittleCoaks]"
        }
    ]
    
    for tag in tags:
        tag['rio_key'] = RIO_KEY
        response = requests.post(f"{BASE_URL}/tag/update", json=tag)
        pprint(response.status_code)
        if (response.status_code == 200):
            pprint(response.json())

def prune_ongoing_game():
    payload = {'rio_key': RIO_KEY}
    payload['seconds'] = 600
    response = requests.post(f"{BASE_URL}/ongoing_game/prune", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def delete_game(game_id):
    payload = {'rio_key': RIO_KEY}
    payload['game_id'] = game_id
    response = requests.post(f"{BASE_URL}/delete_game", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def recalc_ladder(tag_set_id):
    payload = {'tag_set_id': tag_set_id}
    response = requests.post(f"{BASE_URL}/recalc_elo", json=payload)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def submit_game():
    f = open(GAME_JSON_PATH)
    game = json.load(f)
    response = requests.post(f"{BASE_URL}/populate_db", json=game)
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())
    
def get_stat():
    query = "?username=pokebunny&tag=starsoffseason5&exclude_batting=1&exclude_fielding=1"
    response = requests.get(f"{BASE_URL}/stats/{query}")
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def get_generic(url, query = ''):
    response = requests.get(f"{BASE_URL}{url}{query}")
    pprint(response.status_code)
    if (response.status_code == 200):
        pprint(response.json())

def create_user_group():
    f = open(USER_GROUP_PATH)
    user_group = json.load(f)
    user_group['rio_key'] = RIO_KEY
    response = requests.post(f"{BASE_URL}/user_group/create", json=user_group)
    if (response.status_code == 200):
        pprint(response.json())

def get_ip_data():
    payload=dict()
    payload['rio_key'] = RIO_KEY    
    response = requests.post(f"{BASE_URL}/user/get_ip_data", json=payload)
    if (response.status_code == 200):
        pprint(response.json())
    