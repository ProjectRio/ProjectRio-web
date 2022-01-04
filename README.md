## Quick guide of how to send requests/view results on localhost:

## Install Postman Desktop Client and DB Browser for SQLite
- Install Postman Desktop Client (Broswer client cannot be used to send Requests to localhost servers) : https://www.postman.com/downloads/ 
- Install DB Browser for SQLite to easily view data in db.sqlite3 https://sqlitebrowser.org/dl/

## Creating a new sqlite3 database and hosting on localhost:5000
1. Open a terminal of your choice and navigate to project root directory
2. Create a new pipenv instance if necessary
```console
  foo@bar:~$ pipenv --three
```
2.  Install dependencies if necessary
```console
  foo@bar:~$ pipenv install
```
3. Run reset-script.py to remove previous db.sqlite3 file and setup database/host
```console
  foo@bar:~$ python3 reset-script.py
```

## Testing a POST request for /game/
1. Open your Postman desktop client
2. Navigate to 'Workspaces'
3. Create a new Request
4. Choose 'POST'
5. Enter http://127.0.0.1:5000/game/ as Request URL
6. Click 'Body'
7. Choose 'raw' and 'JSON'
8. Paste json game data below
9. Click 'Send'
10. If successful, underneath your entered JSON data another object will appear under Body.

- Possible reasons for a failed Request:
  1.  Reusing a previously entered 'GameId', this is a unique key. Complete 'Creating a new sqlite3 database' and 'Opening app.py on localhost:5000' and try again, OR change GameID value.

## Viewing db.sqlite3
1. Open db.sqlite3 file with DB Browser for SQLite
2. Click browse data
3. Choose table
