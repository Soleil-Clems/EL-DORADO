import sqlite3


def create_schema(conn):
  with open("schema.sql", "r") as f:
    schema = f.read()
  conn.executescript(schema)