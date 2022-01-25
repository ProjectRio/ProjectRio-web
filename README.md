## Quick guide of how to send requests/view results on localhost:

## Install dependencies
1. Open a terminal of your choice and navigate to the project root directory
2. Create a new pipenv instance
```console
  foo@bar:~$ pipenv --three
```
2.  Install dependencies
```console
  foo@bar:~$ pipenv install
```


## Populate database with demo users/games
1. Run reset-script.py to remove previous db.sqlite3 file and create database/host localhost
```console
  foo@bar:~$ python3 reset-script.py
```
2. In another terminal window run populate-db-script.py
```console
  foo@bar:~$ python3 populate-db-script.py
```


## Install Postman Desktop Client and DB Browser for SQLite
- Install Postman Desktop Client to test endpoints (Browser client cannot be used to send Requests to localhost servers): https://www.postman.com/downloads/ 
- Install DB Browser for SQLite to easily view data in db.sqlite3 https://sqlitebrowser.org/dl/

