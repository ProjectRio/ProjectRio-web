from connection import Connection

db = Connection()

def test_connection():
    # Build query
    query = 'SELECT * FROM rio_user WHERE username = %s'
    params = ('PeacockSlayer',)
    
    # Make request
    result = db.query(query, params)

    # Parse request
    username = result[0]['username']

    # Verify username
    assert username == 'PeacockSlayer'
