import os
import subprocess
import random
import json


# Create Character table
print('Creating Character Table:\n')
subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "http://127.0.0.1:5000/create_character_table/"
    ])


# Create Default Tags
print('Creating Tags:\n')
subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "http://127.0.0.1:5000/create_tag_table/"
    ])


# create 6 demo users
f = open("./json/sample-users.json")
users = json.load(f)
print("Creating Users: ")
for user in users["Users"]:
    user_json = json.dumps(user)
    print(user_json)

    # Errors are suppressed because we are using fake email addresses, which return 502s and clog up the console.
    # View statuses on the Localhost pipenv terminal.
    subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "--data", user_json, 
    "http://127.0.0.1:5000/register/"
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT
    )
  

  
print('Uploading Game data:')
for file_path in os.listdir("./json/games/"):
    if file_path != '.DS_Store':
        file = open("./json/games/" + file_path)
        game_data = json.load(file)

        # Replace players with demo players
        demo_players = random.sample(users["Users"], 2)
        away_player = demo_players[0]['Username']
        home_player = demo_players[1]['Username']
        game_data['Away Player'] = away_player
        game_data['Home Player'] = home_player


        print(file_path + ': ' + game_data["GameID"] + ' Players: ' + away_player + ' vs ' + home_player)

        
        # send POST request with editted game data
        # Output suppressed to clearly see which users were selected. 
        # View statuses on the Localhost pipenv terminal.
        game_json = json.dumps(game_data)
        subprocess.run(["curl", "-i",
        "--header", "Content-type: application/json",
        "--request", "POST",
        "--data", game_json,
        "http://127.0.0.1:5000/populate_db/"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
  