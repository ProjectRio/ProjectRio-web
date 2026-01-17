from flask import request, abort
from flask import current_app as app
from ..decorators import api_key_check
from ..models import db, Game, GameHistory, CharacterGameSummary, CharacterPositionSummary, Event, Runner, PitchSummary, ContactSummary, FieldingSummary

@app.route('/delete_game/', methods = ['POST'])
@api_key_check(['Admin', 'TrustedUser'])
def delete_game():
    # Verify game_id
    if request.json["game_id"] is not None:
        try:
            game_id = request.json["game_id"]
            game = Game.query.filter_by(game_id=game_id).first()
        except:
            abort(400, 'Invalid game_id')
    else:
        abort(400, 'Provide a valid game_id')
    
    # try:
    # Get character game summaries
    character_game_summaries = CharacterGameSummary.query.filter_by(game_id=game.game_id).all()

    # Get events
    events = Event.query.filter_by(game_id=game_id).all()
    print('HERE')
    runner_ids = list()
    pitch_summary_ids = list()
    # Get runner_ids and pitch_summary ids
    for event in events:
        runner_ids.append(event.runner_on_0)
        if event.runner_on_1:
            runner_ids.append(event.runner_on_1)
        if event.runner_on_2:
            runner_ids.append(event.runner_on_2)
        if event.runner_on_3:
            runner_ids.append(event.runner_on_3)
        
        if event.pitch_summary_id:
            pitch_summary_ids.append(event.pitch_summary_id)

    # Get contact_summary_ids
    contact_summary_ids = list()
    for pitch_id in pitch_summary_ids:
        pitch = PitchSummary.query.filter_by(id=pitch_id).first()
        if pitch.contact_summary_id:
            contact_summary_ids.append(pitch.contact_summary_id)

    # Get fielding_summary_ids
    fielding_summary_ids = list()
    for contact_id in contact_summary_ids:
        contact = ContactSummary.query.filter_by(id=contact_id).first()
        if contact.fielding_summary_id:
            fielding_summary_ids.append(contact.fielding_summary_id)

    try:
        db.session.query(Event).filter(Event.id.in_([event.id for event in events])).delete()
        db.session.query(Runner).filter(Runner.id.in_(runner_ids)).delete()
        db.session.query(PitchSummary).filter(PitchSummary.id.in_(pitch_summary_ids)).delete()
        db.session.query(ContactSummary).filter(ContactSummary.id.in_(contact_summary_ids)).delete()
        db.session.query(FieldingSummary).filter(FieldingSummary.id.in_(fielding_summary_ids)).delete()
        db.session.query(CharacterGameSummary).filter(CharacterGameSummary.id.in_([character_game_summary.id for character_game_summary in character_game_summaries])).delete()
        db.session.query(CharacterPositionSummary).filter(CharacterPositionSummary.id.in_([character_game_summary.character_position_summary_id for character_game_summary in character_game_summaries])).delete()
        db.session.query(GameHistory).filter(GameHistory.game_id == game_id).delete()
        db.session.query(Game).filter(Game.game_id == game_id).delete()
        
        # commit changes
        db.session.commit()
    except:
        abort(400, "Error attempting to get and delete rows")
    
    return "Game deleted"