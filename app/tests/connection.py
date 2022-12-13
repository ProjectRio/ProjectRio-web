import psycopg2
import psycopg2.extras
import os

class Connection(object):
    def __init__(self):
        self.db = os.getenv("POSTGRES_DB")
        if self.db == "dev":
            self.url = os.getenv("POSTGRES_URL")[:-5]
            self.port = os.getenv("POSTGRES_URL")[-4:]
        else:
            self.url = os.getenv("POSTGRES_URL")[:-6]
            self.port = os.getenv("POSTGRES_URL")[-5:]
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