import subprocess

#remove old database instance
subprocess.run(['del', 'app\db.sqlite3'], shell=True)

#open server/create new db instance
subprocess.run(['pipenv', 'run', 'py', '--3', 'wsgi.py'])
