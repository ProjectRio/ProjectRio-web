from flask import request, abort, jsonify
from flask import current_app as app
from sqlalchemy import text
from ..models import db
from pathlib import Path

cPath_to_sql_dir = 'app/sql'
cFile_for_woba = ["wOBA_Stars_On.txt", "wOBA_Stars_Off.txt", 
                  "Runs_per_PA_Stars_On.txt", "Runs_per_PA_Stars_Off.txt",
                  "wOBA_Scale_Stars_On.txt", "wOBA_Scale_Stars_Off.txt",
                  "wOBA_Stars_On.txt", "wOBA_Stars_Off.txt"]
cFile_for_test = ["table_test.txt"]

def run_sql_files(in_file_list):
    cwd = Path.cwd()
    sql_path = Path.resolve(cwd/cPath_to_sql_dir)

    for file_name in in_file_list:
        sql_file = open(f'{sql_path}/{file_name}', "r")
        sql = sql_file.read()
        db.engine.execute(text(sql))
        print('Executed sql file:', file_name)
    return

@app.route('/gen_woba_data/', methods=['POST'])
def gen_woba_data():
    run_sql_files(cFile_for_woba)
    return jsonify({'Success':200})

def gen_woba_data_routine(app):
    with app.app_context():
        run_sql_files(cFile_for_woba)
        return
