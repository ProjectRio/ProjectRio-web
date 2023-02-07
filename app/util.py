from flask import abort

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