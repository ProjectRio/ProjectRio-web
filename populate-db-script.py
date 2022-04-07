import os
import subprocess
import random
import json
print('\n')
print(
  f'             @@@@@@@@@@@@@@@@\n'        
  f'        @@@@@@##  ##    ###@@@@@\n'
  f'       @@@@# ##    ##      ####@@@@\n'  
  f'    @@@@ ###        ##     ####@@@@@\n'
  f'    @@@@########      ##    ####@@@@\n'
  f'    @@    ##      ##        ##    @@\n'
  f'    @@    ####      ##    ####    @@\n'
  f'    @@    ######    ##  ######    @@\n'
  f'    @@  ########@@@@@@@@########  @@\n'
  f'    @@@@##@@    @@    @@    @@##@@\n' 
  f'      @@@@@@    @@    @@    @@@@@@\n'
  f'      @@@@@@    @@    @@    @@@@@@\n'
  f'        @@@@@@            @@@@@@\n'
  f'            @@@@@@@@@@@@@@@@@\n'
)
print('               Batters up!')


# Create Character table
print('Creating Character Table:')
subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "http://127.0.0.1:5000/create_character_table/"
    ])


print('\n')

# Create Default Tags
print('Creating Tags:')
subprocess.run(["curl", "-i", 
    "--header", "Content-Type: application/json",
    "--request", "POST", 
    "http://127.0.0.1:5000/create_tag_table/"
    ])

print('\n')

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
  
print('\n')
  
print('Uploading Game data:')
for file_path in os.listdir("./json/games/"):
    if file_path != '.DS_Store':
        editted_file = False
        with open("./json/games/" + file_path, 'r') as f:
            game_data = json.load(f)

            # Check if JSON file has replaced player names, if not, replace them.
            demo_players = random.sample(users["Users"], 2)
            away_player = game_data['Away Player'] 
            home_player = game_data['Home Player']

            if game_data['Away Player'][0:8] != 'DemoUser':
                game_data['Away Player'] = demo_players[0]['Username']
                away_player = demo_players[0]['Username']
                editted_file = True

            if game_data['Home Player'][0:8] != 'DemoUser':
                game_data['Home Player'] = demo_players[1]['Username']
                home_player = demo_players[1]['Username']
                eddited_file = True

        if editted_file == True:
            with open("./json/games/" + file_path, 'w') as f:
                f.write(json.dumps(game_data, indent=4))

        print(file_path + ': ' + game_data["GameID"] + ' Players: ' + away_player + ' vs ' + home_player)

        # send POST request with editted game data
        # Output suppressed to clearly see which users were selected. 
        # View statuses on the Localhost pipenv terminal.
        proc = subprocess.run(["curl", "-i",
        "--header", "Content-type: application/json",
        "--request", "POST",
        "--data", f'@./json/games/{file_path}',
        "http://127.0.0.1:5000/populate_db/"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
        )  