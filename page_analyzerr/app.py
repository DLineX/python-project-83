from flask import Flask
import os
import psycopg2
import requests

from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import date


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


def connect():
    database_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    return conn


def normalize(url):
    o = urlparse(url)
    return f'{o.scheme}://{o.netloc}'


def add_url(url):
    created_at = str(date.today())
    with connect().cursor() as curs:
        curs.execute(
            """INSERT INTO urls (name, created_at)
            VALUES (&name, &created_at)
            RETURNING id;""", {"name": url,
                               "created_at": created_at}
        )
    return curs.fetchone()[0]


def find_url(id):
    with connect().cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM urls WHERE id=&id;
            """,
            {"id": id}
        )
        url_id, name, created_at = cursor.fetchone()
        return {
            "id": url_id,
            "name": name,
            "created_at": created_at
        }


def exists_url(url):
    with connect().cursor() as cursor:
        cursor.execute(
            """SELECT id FROM urls WHERE name = &url;""",
            {"url": url}
        )
    if cursor.fetchone():
        return cursor.fetchone()[0]
    else:
        return False


def all_urls():
    with connect().cursor() as curs:
        curs.execute(
            """SELECT 
            urls.id, 
            urls.name, 
            url_checks.created_at as created_at, 
            url_checks.status_code
            FROM urls 
            LEFT JOIN url_checks ON urls.id = url_checks.url_id
            GROUP BY urls.id, urls.name, url_checks.status_code;""")
    urls = []
    for row in curs.fetchall():
        url = {"id": row[0],
               "name": row[1],
               "created_at": row[2],
               "status_code": row[3]}
        urls.append(url)
    return urls


@app.route('/')
def main():
    return render_template('index.html')


# @app.route('/urls/<id>')
# def url_show(id):


@app.post('urls/<id>/checks')
def url_check(id):
    try:
        requests.get(find_url(id)["name"]).raise_for_status()
    except requests.exceptions.RequestException as ex:
        print(ex)
        flash("Неожиданная ошибка при проверке", "error")
        return redirect(url_for("url_show", id=id))
