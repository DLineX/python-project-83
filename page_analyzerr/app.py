from flask import Flask
import os
import psycopg2
import requests
from flask import (render_template, flash, request,
                   redirect, url_for, get_flashed_messages)

from dotenv import load_dotenv
from urllib.parse import urlparse
from validators import url as validator
from datetime import date
from bs4 import BeautifulSoup


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
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """INSERT INTO urls (name, created_at)
            VALUES (%(name)s, %(created_at)s)
            RETURNING id;""", {"name": url,
                               "created_at": created_at}
        )
        return curs.fetchone()[0]


def find_url(id):
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """
            SELECT * FROM urls WHERE id=%(id)s;
            """,
            {"id": id}
        )
        url_id = curs.fetchone()
        name = curs.fetchone()
        created_at = curs.fetchone()
        return {
            "id": url_id,
            "name": name,
            "created_at": created_at
        }


def exists_url(url):
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """SELECT id FROM urls WHERE name = %(url)s;""",
            {"url": url}
        )
        if curs.fetchone():
            return curs.fetchone()[0]
        return False


def all_urls():
    conn = connect()
    with conn.cursor() as curs:
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
        rows = curs.fetchall()
        for row in rows:
            url = {
                "id": row[0],
                "name": row[1],
                "created_at": row[2],
                "status_code": row[3]
            }
        urls.append(url)
        return urls


@app.route('/')
def main():
    return render_template('index.html')


@app.route('/urls')
def get_urls():
    return render_template('urls.html', urls=all_urls())


@app.post('/urls')
def urls_add():
    url = normalize(request.form.get('url'))
    if not validator(url):
        flash("Некорректный URL", "error")
        return render_template(
            'index.html',
            messages=get_flashed_messages(with_categories=True)
        ), 422
    if exists_url(url):
        flash("Страница существует", "error")
        return redirect(url_for('url_show', id=exists_url(url)))
    flash("Страница успешно добавлена", "success")
    return redirect(url_for('url_show', id=add_url(url)))


def all_checks(id):
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """SELECT id,
            status_code,
            COALESCE(h1,
            title,
            description),
            DATE(created_at)
            FROM url_checks
            WHERE url_id = id
            ORDER BY id;""", (id,)
        )
        checks = []
        rows = curs.fetchall()
        for row in rows:
            check = {
                "id": row[0],
                "status_code": row[1],
                "h1": row[2],
                "title": row[3],
                "description": row[4],
                "created_at": row[5]
            }
        checks.append(check)
        return checks


@app.route('/urls/<id>')
def url_show(id):
    url = find_url(id)
    checks = all_checks(id)
    messages = get_flashed_messages(with_categories=True)
    return render_template("show.html", url=url,
                           messages=messages, checks=checks)


def check_url(id, status_code, h1, title, description):
    created_at = str(date.today())
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """INSERT INTO url_checks (url_id, status_code, h1,
            title, description, created_at)
            VALUES (%(url_id)s, %(status_code)s, %(h1)s, %(title)s,
            %(description)s, %(created_at)s)
            RETURNING url_id, created_at;""",
            {"url_id": id,
             "status_code": status_code,
             "h1": h1,
             "title": title,
             "description": description,
             "created_at": created_at}
        )


@app.post('/urls/<id>/checks')
def url_check(id):
    try:
        response = requests.get(find_url(id)["name"])
        response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        print(ex)
        flash("Неожиданная ошибка при проверке", "error")
        return redirect(url_for("url_show", id=id))

    status_code = response.status_code
    soup = BeautifulSoup(response.text, "lxml")
    h1 = soup.find("h1")
    h1 = h1.text if h1 else ""
    title = soup.find("title")
    title = title.text if title else ""
    description = soup.find("meta", {"name": "description"})
    description = description["description"] if description else ""

    check_url(id, status_code=status_code, h1=h1, title=title,
              description=description)
    flash("Url успешно проверен", "success")
    return redirect(url_for("url_show", id=id))
