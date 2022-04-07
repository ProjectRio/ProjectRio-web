import subprocess
from os.path import exists
import sys


print('\n')
print(
  f'                            @@@@@@@@@@@@@@@@\n'        
  f'                        @@@@@@##  ##    ###@@@@@\n'
  f'                      @@@@# ##    ##      ####@@@@\n'  
  f'                    @@@@ ###        ##     ####@@@@@\n'
  f'                    @@@@########      ##    ####@@@@\n'
  f'                    @@    ##      ##        ##    @@\n'
  f'                    @@    ####      ##    ####    @@\n'
  f'                    @@    ######    ##  ######    @@\n'
  f'                    @@  ########@@@@@@@@########  @@\n'
  f'                    @@@@##@@    @@    @@    @@##@@\n' 
  f'                      @@@@@@    @@    @@    @@@@@@\n'
  f'                      @@@@@@    @@    @@    @@@@@@\n'
  f'                        @@@@@@            @@@@@@\n'
  f'                           @@@@@@@@@@@@@@@@@@\n'
  )
print(
  f'#####    ##   ######         #####   ######      ###     ######    #####\n'
  f'##  ##   ##   ##  ##        ##         ##       #   #      ##     ##\n'
  f'#####    ##   ##  ##         ####      ##      #######     ##      ####\n'
  f'##  #    ##   ##  ##            ##     ##      ##   ##     ##         ##\n'
  f'##  ##   ##   ######        #####      ##      ##   ##     ##     #####\n'
)
print('                             Welcome to Rio!')
print('\n')

if exists('./app/db.sqlite3'):
  response = input('You already have a db.sqlite3 instance...\nWould you like to delete it? (Y/N): ')
  if response == 'Y' or response == 'y':
    #remove old database instance
    subprocess.run(['rm', './app/db.sqlite3'])
    print('db.sqlite3 instance deleted...')
    print('Run python3 populate-db-script.py in a separate window to populate a new instance.')


print('Starting server...')
#open server/create new db instance
subprocess.run(['pipenv', 'run', 'python3', 'wsgi.py'])
