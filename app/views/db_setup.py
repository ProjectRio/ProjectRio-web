from flask import request, abort
from flask import current_app as app
from ..models import *
from ..consts import *
import json
import os

# === Initalize Character Tables And Ranked/Superstar Tags ===
@app.route('/init_db/', methods=['POST'])
def init_db():
    if os.getenv('RESET_DB') == request.json['RESET_DB']:
        try:
            engine = db.get_engine()
            Event.__table__.drop(engine)
            Runner.__table__.drop(engine)
            PitchSummary.__table__.drop(engine)
            ContactSummary.__table__.drop(engine)
            FieldingSummary.__table__.drop(engine)
            CharacterGameSummary.__table__.drop(engine)
            CharacterPositionSummary.__table__.drop(engine)
            GameTag.__table__.drop(engine)        
            Game.__table__.drop(engine)
            db.create_all()
            create_character_tables()
            #create_default_tags()
            create_default_groups()
            create_official_infrastructure()
            return 'DB Init'
        except:
            abort(400, "Error dropping or creating tables.")  
    else:
        abort(400, 'Invalid password')
    return 'Success...'

# **DANGER**
# Completely wipe the DB
@app.route('/wipe_db/', methods=['POST'])
def wipe_db():
    if os.getenv('RESET_DB') == request.json['RESET_DB']:
        db.drop_all()
        db.create_all()
        create_character_tables()
        create_default_groups()
        create_official_infrastructure()
        return 'DB Wiped'
    else:
        abort(401, 'Invalid password')
    return 'Success...'

def create_character_tables():
    f = open('./json/characters.json')
    character_list = json.load(f)["Characters"]

    for character in character_list:
        chemistry_table = ChemistryTable(
            mario = character['Mario (0x3b)'],
            luigi = character['Luigi (0x3c)'],
            dk = character['DK (0x3d)'],
            diddy = character['Diddy (0x3e)'],
            peach = character['Peach (0x3f)'],
            daisy = character['Daisy (0x40)'],
            yoshi = character['Yoshi (0x41)'],
            baby_mario = character['Baby Mario (0x42)'],
            baby_luigi = character['Baby Luigi (0x43)'],
            bowser = character['Bowser (0x44)'],
            wario = character['Wario (0x45)'],
            waluigi = character['Waluigi (0x46)'],
            koopa_r = character['Koopa(R) (0x47)'],
            toad_r = character['Toad(R) (0x48)'],
            boo = character['Boo (0x49)'],
            toadette = character['Toadette (0x4a)'],
            shy_guy_r = character['Shy Guy(R) (0x4b)'],
            birdo = character['Birdo (0x4c)'],
            monty = character['Monty (0x4d)'],
            bowser_jr = character['Bowser Jr (0x4e)'],
            paratroopa_r = character['Paratroopa(R) (0x4f)'],
            pianta_b = character['Pianta(B) (0x50)'],
            pianta_r = character['Pianta(R) (0x51)'],
            pianta_y = character['Pianta(Y) (0x52)'],
            noki_b = character['Noki(B) (0x53)'],
            noki_r = character['Noki(R) (0x54)'],
            noki_g = character['Noki(G) (0x55)'],
            bro_h = character['Bro(H) (0x56)'],
            toadsworth = character['Toadsworth (0x57)'],
            toad_b = character['Toad(B) (0x58)'],
            toad_y = character['Toad(Y) (0x59)'],
            toad_g = character['Toad(G) (0x5a)'],
            toad_p = character['Toad(P) (0x5b)'],
            magikoopa_b = character['Magikoopa(B) (0x5c)'],
            magikoopa_r = character['Magikoopa(R) (0x5d)'],
            magikoopa_g = character['Magikoopa(G) (0x5e)'],
            magikoopa_y = character['Magikoopa(Y) (0x5f)'],
            king_boo = character['King Boo (0x60)'],
            petey = character['Petey (0x61)'],
            dixie = character['Dixie (0x62)'],
            goomba = character['Goomba (0x63)'],
            paragoomba = character['Paragoomba (0x64)'],
            koopa_g = character['Koopa(G) (0x65)'],
            paratroopa_g = character['Paratroopa(G) (0x66)'],
            shy_guy_b = character['Shy Guy(B) (0x67)'],
            shy_guy_y = character['Shy Guy(Y) (0x68)'],
            shy_guy_g = character['Shy Guy(G) (0x69)'],
            shy_guy_bk = character['Shy Guy(Bk) (0x6a)'],
            dry_bones_gy = character['Dry Bones(Gy) (0x6b)'],
            dry_bones_g = character['Dry Bones(G) (0x6c)'],
            dry_bones_r = character['Dry Bones(R) (0x6d)'],
            dry_bones_b = character['Dry Bones(B) (0x6e)'],
            bro_f = character['Bro(F) (0x6f)'],
            bro_b = character['Bro(B) (0x70)'],
        )

        db.session.add(chemistry_table)
        db.session.commit()

        character = Character(
            char_id = int(character['Char Id'], 16),
            chemistry_table_id = chemistry_table.id,
            name = character['Char Name'],
            name_lowercase = character['Char Name'].lower(),
            starting_addr = character['Starting Addr'],
            curve_ball_speed = character['Curve Ball Speed (0x0)'],
            fast_ball_speed = character['Fast Ball Speed (0x1)'],
            curve = character['Curve (0x3)'],
            fielding_arm = character['Fielding Arm (righty:0,lefty:1) (0x26)'],
            batting_stance = character['Batting Stance (righty:0,lefty:1) (0x27)'],
            nice_contact_spot_size = character['Nice Contact Spot Size (0x28)'],
            perfect_contact_spot_size = character['Perfect Contact Spot Size (0x29)'],
            slap_hit_power = character['Slap Hit Power (0x2a)'],
            charge_hit_power = character['Charge Hit Power (0x2b)'],
            bunting = character['Bunting (0x2c)'],
            hit_trajectory_mpp = character['Hit trajectory (mid:0,pull:1,push:2) (0x2d)'],
            hit_trajectory_mhl = character['Hit trajectory (mid:0,high:1,low:2) (0x2e)'],
            speed = character['Speed (0x2f)'],
            throwing_arm = character['Throwing Arm (0x30)'],
            character_class = character['Character Class (balance:0,power:1,speed:2,technique:3) (0x31)'],
            weight = character['Weight (0x32)'],
            captain = character['Captain (true:1,false:0) (0x33)'],
            captain_star_hit_or_pitch = character['Captain Star Hit/Pitch (0x34)'],
            non_captain_star_swing = character['Non Captain Star Swing (1:pop fly,2:grounder,3:line drive) (0x35)'],
            non_captain_star_pitch = character['Non Captain Star Pitch (0x36)'],
            batting_stat_bar = character['Batting Stat Bar (0x37)'],
            pitching_stat_bar = character['Pitching Stat Bar (0x38)'],
            running_stat_bar = character['Running Stat Bar (0x39)'],
            fielding_stat_bar = character['Fielding Stat Bar (0x3a)'],
        )

        db.session.add(character)

    db.session.commit()

    return 'Characters added...\n'

def create_default_tags():
    ranked = Tag(
        in_tag_name = "Ranked",
        in_desc = "Tag for Ranked games",
        in_tag_type = "Global",
        in_comm_id = None
    )

    unranked = Tag(
        in_tag_name = "Unranked",
        in_desc = "Tag for Unranked games",
        in_tag_type = "Global",
        in_comm_id = None
    )

    superstar = Tag(
        in_tag_name = "Superstar",
        in_desc = "Tag for Stars On",
        in_tag_type = "Global",
        in_comm_id = None
    )

    normal = Tag(
        in_tag_name = "Normal",
        in_desc = "Tag for Normal games",
        in_tag_type = "Global",
        in_comm_id = None
    )

    netplay = Tag(
        in_tag_name = "Netplay",
        in_desc = "Tag for Netplay games",
        in_tag_type = "Global",
        in_comm_id = None
    )

    local = Tag(
        in_tag_name = "Local",
        in_desc = "Tag for Local games",
        in_tag_type = "Global",
        in_comm_id = None
    )

    db.session.add(ranked)
    db.session.add(unranked)
    db.session.add(superstar)
    db.session.add(normal)
    db.session.add(netplay)
    db.session.add(local)
    db.session.commit()

    return 'Tags created... \n'

def create_default_groups():
    admin = UserGroup(in_group_name='Admin')
    developer = UserGroup(in_group_name='Developer')
    patron_fan = UserGroup(in_group_name='Patron: Fan')
    patron_rookie = UserGroup(in_group_name='Patron: Rookie')
    patron_mvp = UserGroup(in_group_name='Patron: MVP')
    patron_hof = UserGroup(in_group_name='Patron: Hall of Famer')
    general = UserGroup(in_group_name='General')

    # Limits for Patron perks - TODO possibly make more robust
    # Will have an endpoint to adjust
    admin.sponsor_limit = 999
    developer.sponsor_limit = 999
    patron_fan.sponsor_limit = 0
    patron_rookie.sponsor_limit = 1
    patron_mvp.sponsor_limit = 5
    patron_hof.sponsor_limit = 10
    general.sponsor_limit = 0

    db.session.add(admin)
    db.session.add(developer)
    db.session.add(patron_fan)
    db.session.add(patron_rookie)
    db.session.add(patron_mvp)
    db.session.add(patron_hof)
    db.session.add(general)
    db.session.commit()


def create_official_infrastructure():
    admin_user = create_admin_users()
    create_official_comms(admin_user)

def create_admin_users():
    admin_user = RioUser('ProjectRio', 'projectrio.dev@gmail.com', secrets.token_urlsafe(32))
    admin_user.verified = True
    admin_user.active_url = None
    db.session.add(admin_user)
    db.session.commit()

    #Get admin group
    user_group = UserGroup.query.filter_by(name_lowercase='admin').first()

    #Add admin user to group
    new_user_group_user = UserGroupUser(
        user_id=admin_user.id,
        user_group_id=user_group.id
    )
    db.session.add(new_user_group_user)
    db.session.commit()

    return admin_user

def create_official_comms(admin_user):
    new_comm = Community('OfficialRanked', admin_user.id, 'Official', False, cACTIVE_TAGSET_LIMIT, True, 'Official community of ProjectRio')
    db.session.add(new_comm)
    db.session.commit()

    # === Create CommunityUser (admin)
    new_comm_user = CommunityUser(admin_user.id, new_comm.id, True, False, True)
    db.session.add(new_comm_user)
    db.session.commit()

    # === Create Community Tag ===
    new_comm_tag = Tag(new_comm.id, new_comm.name, "Community", f"Community tag for {new_comm.name}")
    db.session.add(new_comm_tag)
    db.session.commit()

@app.route('/restore_users/', methods=['GET'])
def restore_users():
    if os.getenv('RESET_DB') == request.json['RESET_DB']:
        try:
            f = open('./json/rio_user.json')
            rio_users = json.load(f)
            for user in rio_users:
                new_user = RioUser(user['username'], user['username_lowercase'], user['email'], "temp")
                new_user.password = user['password']
                new_user.verified = user['verified']
                new_user.rio_key = user['rio_key']
                new_user.active_url = user['active_url']
                db.session.add(new_user)
            db.session.commit()
        except:
            abort(400, "Error restoring users.")  
    else:
        abort(400, 'Invalid password')
    return 'Success...'