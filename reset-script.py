import subprocess

# Remove previous database instance
subprocess.run(['rm', 'db.sqlite3'])

#create new database instance
subprocess.run(['pipenv', 'run', 'python3', 'pipenv-script.py'])
subprocess.run(['open','db.sqlite3'])

#host app on localhost
subprocess.run(['pipenv','run','python3','app.py'])
