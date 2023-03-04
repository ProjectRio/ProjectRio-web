from flask import abort
import string

def calculate_era(runs_allowed, outs_pitched):
    if outs_pitched == 0 and runs_allowed > 0:
        return -abs(runs_allowed)
    elif outs_pitched > 0:
        return runs_allowed/(outs_pitched/3)
    else:
        return 0

def format_tuple_for_SQL(in_tuple):
    sql_tuple = "(" + ",".join(repr(v) for v in in_tuple) + ")"
    
    return (sql_tuple, (len(in_tuple) == 0))

def format_list_for_SQL(in_list):
    return format_tuple_for_SQL(tuple(in_list))


def sanatize_ints(str):
  not_statement = True if str[0] == '!' else False

  arr = []
  if not_statement:
    str = str[1:]

  if '!' in str:
    abort(400, 'Cannot have ! after param[0]')

  arr = str.split('_')
  final_arr = list()
  for val in arr:
    if '-' in val:
      temp_arr = val.split('-')
      for num in list(range(int(temp_arr[0]), int(temp_arr[1]) + 1)):
        final_arr.append(num)
    else:
      final_arr.append(int(val))

  return final_arr

def lower_and_remove_nonalphanumeric(in_str):
  return (''.join([i for i in in_str if i.isalnum()])).lower()

def validate_gecko_code(in_str):
  idx = 0
  for char in in_str:
    if idx == 17:
      if char != '\n':
        return False
      idx = 0
    elif idx == 8:
      if char != ' ':
        return False  
      idx+=1
    elif idx <= 16:
      if char not in string.hexdigits:
        return False
      idx+=1
  #After the for loop 
  if (idx != 0): #Loop ended in the middle of a line
    return False
  return True