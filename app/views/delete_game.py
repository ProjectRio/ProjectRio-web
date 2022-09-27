from flask import request, abort
from flask import current_app as app
from ..models import db, Game, CharacterGameSummary, CharacterPositionSummary, Event, Runner, PitchSummary, ContactSummary, FieldingSummary, GameTag

@app.route('/delete_game/', methods = ['POST'])
def delete_game():
    #Not ready for production (Untested)
    if (app.config['rio_env'] == "production"):
        return abort(404, description='Endpoint not ready for production')

    # Verify key is valid


    # Verify game_id
    if request.args.get("game_id") is not None:
        try:
            game_id = request.args.get("game_id")
            game = Game.query.filter_by(game_id=game_id).first()
        except:
            abort(400, 'Invalid game_id')
    else:
        abort(400, 'Provide a valid game_id')
    
    try:
        # Get character game summaries
        character_game_summaries = CharacterGameSummary.query.filter_by(game_id=game.game_id).all()

        # Get events
        events = Event.query.filter_by(game_id=game_id).all()

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
        for pitch in pitch_summary_ids:
            if pitch.contact_summary_id:
                contact_summary_ids.append(pitch.contact_summary_id)

        # Get fielding_summary_ids
        fielding_summary_ids = list()
        for contact in contact_summary_ids:
            if contact.fielding_summary_id:
                fielding_summary_ids.append(contact.id)

        # delete runners
        db.session.delete(Runner).where(Runner.id.in_(runner_ids))
                
        # delete fielding_summary_ids
        db.session.delete(FieldingSummary).where(FieldingSummary.id.in_(fielding_summary_ids))

        # delete contact_summarys
        db.session.delete(ContactSummary).where(ContactSummary.id.in_(contact_summary_ids))

        # delete pitch_summarys
        db.session.delete(PitchSummary).where(PitchSummary.id.in_(runner_ids))

        # delete events
        db.session.delete(Event).where(Event.id.in_([event.id for event in events]))

        # delete game_tag entries
        db.session.delete(GameTag).where(GameTag.game_id == game_id)

        # Delete character_position_summaries 
        db.session.delete(CharacterPositionSummary).where(CharacterPositionSummary.id.in_([character_game_summary.character_position_summary_id for character_game_summary in character_game_summaries]))
        
        # delete character_game_summaries
        db.session.delete(CharacterGameSummary).where(CharacterGameSummary.id.in_([character_game_summary.id for character_game_summary in character_game_summaries]))
        
        # delete game
        db.session.delete(Game).where(Game.game_id == game_id)

        # commit changes
        db.session.commit()
    except:
        abort(400, "Error attempting to get and delete rows")
    
    return "Game deleted"