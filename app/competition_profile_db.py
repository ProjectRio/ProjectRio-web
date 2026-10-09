'''Database access for competition_profile (rules in competition_profile.py).

sync_competitions() runs at the start of the nightly RE24 job:
  1. On an empty table, load the reviewed starting list,
     app/data/competition_profile_seed.csv (one row per tag set that exists).
  2. Copy tag_set.name into competition wherever a tag set was renamed.
  3. Give every tag set without a row one: 'auto' when it continues a reviewed
     series, otherwise 'pending' with every flag off.
'''
import csv
import time
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

from .models import db, CompetitionProfile
from .competition_profile import cFLAGS, profile_for_new, rule_names

cSEED_PATH = Path(__file__).resolve().parent / 'data' / 'competition_profile_seed.csv'

cCOLUMNS = ('tag_set_id', 'competition', 'category', 'type') + cFLAGS + ('status', 'note')

cINSERT_SQL = text('''
    INSERT INTO competition_profile
        (tag_set_id, competition, category, type, q_ranked, q_league_stats,
         q_player_stats, q_character_stats, q_pick_rates, status, note, updated_at)
    SELECT ts.id, ts.name, :category, :type, :q_ranked, :q_league_stats,
           :q_player_stats, :q_character_stats, :q_pick_rates, :status, :note, :now
    FROM tag_set ts
    WHERE ts.id = :tag_set_id
    ON CONFLICT (tag_set_id) DO NOTHING
''')

cRENAME_SQL = text('''
    UPDATE competition_profile cp
    SET competition = ts.name
    FROM tag_set ts
    WHERE ts.id = cp.tag_set_id AND cp.competition IS DISTINCT FROM ts.name
''')

cNEW_SQL = text('''
    SELECT ts.id, ts.name, ts.name_lowercase, ts.type
    FROM tag_set ts
    WHERE NOT EXISTS (SELECT 1 FROM competition_profile cp WHERE cp.tag_set_id = ts.id)
    ORDER BY ts.id
''')

cRULE_TAGS_SQL = text('''
    SELECT x.tagset_id, t.name, t.tag_type
    FROM tag_set_tag x JOIN tag t ON t.id = x.tag_id
''')


def read_seed(path=cSEED_PATH):
    '''The starting list as dicts with real booleans.'''
    with open(path, newline='', encoding='utf-8') as fh:
        rows = []
        for row in csv.DictReader(fh):
            row = {key: row[key] for key in cCOLUMNS}
            row['tag_set_id'] = int(row['tag_set_id'])
            for flag in cFLAGS:
                row[flag] = row[flag].strip().lower() == 'true'
            row['note'] = row['note'] or None
            rows.append(row)
    return rows


def _insert(rows, now):
    written = 0
    for row in rows:
        params = {key: row[key] for key in cCOLUMNS if key != 'competition'}
        params['now'] = now
        written += db.session.execute(cINSERT_SQL, params).rowcount
    return written


def seed_if_empty(now):
    '''Load the starting list into an empty table. Returns rows written.'''
    if db.session.query(CompetitionProfile.tag_set_id).first() is not None:
        return 0
    return _insert(read_seed(), now)


def add_new_competitions(now):
    '''A row for every tag set that has none. Returns the new rows.'''
    new = [dict(r._mapping) for r in db.session.execute(cNEW_SQL)]
    if not new:
        return []
    tags = defaultdict(list)
    for tag_set_id, name, tag_type in db.session.execute(cRULE_TAGS_SQL):
        tags[tag_set_id].append((name, tag_type))
    reviewed = []
    for profile in CompetitionProfile.query.filter_by(status='reviewed').all():
        row = profile.to_dict()
        row['rules'] = rule_names(tags[profile.tag_set_id])
        reviewed.append(row)
    rows = [profile_for_new(tag_set, rule_names(tags[tag_set['id']]), reviewed) for tag_set in new]
    _insert(rows, now)
    return rows


def sync_competitions():
    '''Seed, follow renames and sort new competitions; one commit.'''
    now = int(time.time())
    seeded = seed_if_empty(now)
    renamed = db.session.execute(cRENAME_SQL).rowcount
    added = add_new_competitions(now)
    db.session.commit()
    return {
        'seeded': seeded,
        'renamed': renamed,
        'auto': [r['competition'] for r in added if r['status'] == 'auto'],
        'pending': [r['competition'] for r in added if r['status'] == 'pending'],
    }
