import os
import subprocess
import random
import json


# Create Character table
print('Creating Character Table:\n')
subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "http://127.0.0.1:5000/create_character_tables/"
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
        # Choose two random players for this game
        players = random.sample(users["Users"], 2)
        away_player = players[0]['Username']
        home_player = players[1]['Username']
        print(away_player + ' vs ' + home_player)

        # Replace game user names with demo users
        file = open("./json/games/" + file_path)
        game_data = json.load(file)
        game_data['Away Player'] = away_player
        game_data['Home Player'] = home_player

        # send POST request with editted game data
        # Output suppressed to clearly see which users were selected. 
        # View statuses on the Localhost pipenv terminal.
        game_json = json.dumps(game_data)
        subprocess.run(["curl", "-i",
        "--header", "Content-type: application/json",
        "--request", "POST",
        "--data", game_json,
        "http://127.0.0.1:5000/upload_game_data/"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
  