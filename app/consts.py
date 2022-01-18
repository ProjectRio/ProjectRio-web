
# Dicts to interpret result of play

cPLAY_RESULT_INVLD = {0: 'Strike/Foul'}
cPLAY_RESULT_OUT  = {
    1: 'Strikeout',
    4: 'Out',
    5: 'Caught',
    6: 'Caught', 
    0xE: 'SacFly'
}
cPLAY_RESULT_SAFE = {
    2: 'BB', 
    3: 'HBP', 
    7: 'Single', 
    8: 'Double',
    9: 'Triple',
    0xA: 'Homerun',
    0x10: 'ClearedBases'
}
cPLAY_RESULT_BUNT = {0xD: 'Bunt'}
