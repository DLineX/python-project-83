import os
import psycopg2
from psycopg2.extras import NamedTupleCursor
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv()


def connect():
    database_url = os.getenv('DATABASE_URL')
    return psycopg2.connect(database_url)


def normalize(url):
    o = urlparse(url)
    return f'{o.scheme}://{o.netloc}'


def add_url(url):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """INSERT INTO urls (name)
            VALUES (%s)
            RETURNING id;""", (str(url),)
        )
        conn.commit()
        return curs.fetchone()


def find_url(id):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """
            SELECT * FROM urls WHERE id=(%s);
            """,
            (id,))
        return curs.fetchone()


def exists_url(name):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """SELECT id FROM urls WHERE name = (%s);""",
            (name,)
        )
        return curs.fetchone()


def all_urls():
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """SELECT
            urls.id,
            urls.name,
            url_checks.created_at as date,
            url_checks.status_code,
            MAX(url_checks.url_id)
            FROM urls
            LEFT JOIN url_checks ON urls.id = url_checks.url_id
            GROUP BY urls.id, urls.name, url_checks.status_code,
            url_checks.created_at;""")
        return curs.fetchall()


def all_checks(id):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """SELECT * FROM url_checks
            WHERE url_id = (%s);""", (id,)
        )
        return curs.fetchall()


def check_url(all_data):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """INSERT INTO url_checks (url_id, status_code, h1,
            title, description)
            VALUES (%(url_id)s, %(status_code)s, %(h1)s, %(title)s,
            %(description)s);""",
            all_data
        )
        conn.commit()


def beautiful_soup(content):
    soup = BeautifulSoup(content, 'lxml')
    h1 = soup.h1.text if soup.h1 else ''
    title = soup.title.text if soup.title else ''
    description = ''
    meta = soup.find("meta", {"name": "description"})
    if meta:
        description = meta.get('content', '')
    return {'h1': h1,
            'title': title,
            'description': description}
