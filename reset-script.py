import subprocess

#remove old database instance
subprocess.run(['rm', 'app/db.sqlite3'])

#open server/create new db instance
subprocess.run(['pipenv', 'run', 'python3', 'wsgi.py'])

#open db for viewing
# subprocess.run(['open','app/db.sqlite3'])
