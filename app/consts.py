# Game parameter bounds (used for input validation)
cMAX_CHAR_ID       = 54   # char_ids 0-53 (range() exclusive upper bound)
cMAX_CONTACT_TYPES = 6    # contact types 0-5
cMAX_CHEM_LINKS    = 4    # chem links 0-3
cMAX_FIELDER_POS   = 9    # fielder positions 0-8
cMAX_INNING        = 50   # reasonable upper bound
cMAX_BALLS         = 4    # 0-3
cMAX_STRIKES       = 3    # 0-2
cMAX_OUTS          = 3    # 0-2
cMAX_SCORE         = 50   # reasonable upper bound
cMAX_FINAL_RESULT  = 17   # result_of_ab values 0-16

# URL for frontend
cURL = "https://projectrio.pages.dev"

#Rio Web Version
cRIO_WEB_VERSION = "1.6.2"

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

# Consts used to create profile query
cCharacters = 1
cCaptains = 2

cDefaultEloRating = 1500
cDefaultEloRd = 300
cDefaultEloVol = 0.06

cTYPE_OF_SWING = {
    0: "None",
    1: "Slap",
    2: "Charge",
    3: "Star",
    4: "Bunt"
}

cHANDEDNESS = {
    0: "Right",
    1: "Left"
}

cTAG_TYPES = {
    0: "Component",
    1: "Competition",
    3: "Community",
    4: "Client Code",
    5: "Gecko Code",
    6: "Test"
}

cTAG_SET_TYPES = {
    0: "Season",
    1: "League",
    3: "Tournament",
    4: "Custom",
    5: "Test"
}

cCOMM_TYPES = {
    0: "Official",
    1: "Unofficial",
}

cPATREON_TIERS = ['Patron: Fan', 'Patron: Rookie', 'Patron: MVP', 'Patron: Hall of Famer']

cACTIVE_TAGSET_LIMIT = 5

cCHAR_NAME = {
    0:  "Mario",
    1:  "Luigi",
    2:  "DK",
    3:  "Diddy",
    4:  "Peach",
    5:  "Daisy",
    6:  "Yoshi",
    7:  "Baby Mario",
    8:  "Baby Luigi",
    9:  "Bowser",
    10: "Wario",
    11: "Waluigi",
    12: "Koopa(G)",
    13: "Toad(R)",
    14: "Boo",
    15: "Toadette",
    16: "Shy Guy(R)",
    17: "Birdo",
    18: "Monty",
    19: "Bowser Jr",
    20: "Paratroopa(R)",
    21: "Pianta(B)",
    22: "Pianta(R)",
    23: "Pianta(Y)",
    24: "Noki(B)",
    25: "Noki(R)",
    26: "Noki(G)",
    27: "Bro(H)",
    28: "Toadsworth",
    29: "Toad(B)",
    30: "Toad(Y)",
    31: "Toad(G)",
    32: "Toad(P)",
    33: "Magikoopa(B)",
    34: "Magikoopa(R)",
    35: "Magikoopa(G)",
    36: "Magikoopa(Y)",
    37: "King Boo",
    38: "Petey",
    39: "Dixie",
    40: "Goomba",
    41: "Paragoomba",
    42: "Koopa(R)",
    43: "Paratroopa(G)",
    44: "Shy Guy(B)",
    45: "Shy Guy(Y)",
    46: "Shy Guy(G)",
    47: "Shy Guy(Bk)",
    48: "Dry Bones(Gy)",
    49: "Dry Bones(G)",
    50: "Dry Bones(R)",
    51: "Dry Bones(B)",
    52: "Bro(F)",
    53: "Bro(B)",
}
