import subprocess

#remove old database instance
subprocess.run(['rm', './app/db.sqlite3'])

#open server/create new db instance
subprocess.run(['pipenv', 'run', 'python3', 'wsgi.py'])
