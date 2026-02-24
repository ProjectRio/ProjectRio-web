import psycopg2
import psycopg2.extras
import os

class Connection(object):
    def __init__(self):
        self.db = os.getenv("POSTGRES_DB")
        postgres_url = os.getenv("POSTGRES_URL", "localhost:5432")
        host_port = postgres_url.rsplit(":", 1)
        self.url = host_port[0]
        self.port = host_port[1] if len(host_port) > 1 else "5432"
        self.user = os.getenv("POSTGRES_USER")
        self.pw = os.getenv("POSTGRES_PW")

    def query(self, query, params):
        try:
            connection = psycopg2.connect(
                user=self.user,
                host=self.url,
                database=self.db,
                password=self.pw,
                port=self.port
            )
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            result = cursor.fetchall()
        except (Exception, psycopg2.Error) as error:
            print("Error fetching data from PostgreSQL table", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                return result