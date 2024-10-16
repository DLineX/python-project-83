from flask import Flask
import os
import psycopg2
from psycopg2.extras import NamedTupleCursor
import requests
from flask import (render_template, flash, request,
                   redirect, url_for, get_flashed_messages)

from dotenv import load_dotenv
from urllib.parse import urlparse
import validators
from datetime import date
from bs4 import BeautifulSoup


load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
app = Flask(__name__)
app.secret_key = SECRET_KEY


def connect():
    database_url = os.getenv('DATABASE_URL')
    return psycopg2.connect(database_url)


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
        conn.commit()
        return curs.fetchone()


def find_url(id):
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """
            SELECT * FROM urls WHERE id=%(id)s;
            """,
            {'id': id})
        return curs.fetchone()


def exists_url(url):
    conn = connect()
    with conn.cursor() as curs:
        curs.execute(
            """SELECT id FROM urls WHERE name = %(url)s;""",
            {"url": url}
        )
        id = curs.fetchone()
        if id:
            return id
        else:
            return False


def all_urls():
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """SELECT
            urls.id,
            urls.name,
            url_checks.created_at as date,
            url_checks.status_code
            MAX(url_checks.url_id)
            FROM urls
            LEFT JOIN url_checks ON urls.id = url_checks.url_id
            GROUP BY urls.id, urls.name, url_checks.status_code,
            url_checks.created_at;""")
        return curs.fetchall()


@app.get('/')
def main():
    return render_template('form.html')


@app.get('/urls')
def get_urls():
    urls = all_urls()
    return render_template('urls.html', urls=urls)


@app.post('/urls')
def urls_add():
    url = request.form.to_dict()['url'].strip()
    if not validators.url(url):
        flash("Некорректный URL", "danger")
        return render_template(
            'form.html',
            url=url
        ), 422
    url = normalize(url)
    url_finds = exists_url(url)
    if url_finds:
        flash("Страница существует", "info")
        id = url_finds.id
        return redirect(url_for('url_show', id=id))
    else:
        id = add_url(url)
        flash("Страница успешно добавлена", "success")
        return redirect(url_for('url_show', id=id.id))


def all_checks(id):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """SELECT * FROM url_checks
            WHERE url_id = (%s);""", (id,)
        )
        return curs.fetchall()


@app.get('/urls/<int:id>')
def url_show(id):
    url = find_url(id)
    url_check = all_checks(id)
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        "show.html",
        url=url,
        messages=messages,
        url_check=url_check
    )


def check_url(all_data):
    conn = connect()
    with conn.cursor(cursor_factory=NamedTupleCursor) as curs:
        curs.execute(
            """INSERT INTO url_checks (url_id, status_code, h1,
            title, description, created_at)
            VALUES (%(url_id)s, %(status_code)s, %(h1)s, %(title)s,
            %(description)s, %(created_at)s)
            RETURNING url_id, created_at;""",
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


@app.post('/urls/<int:id>/checks')
def url_check(id):
    url = find_url(id)
    try:
        response = requests.get(url.name)
        response.raise_for_status()
        all_data = beautiful_soup(response.text)
        all_data['status_code'] = response.status_code
        all_data['url_id'] = id
        flash("Url успешно проверен", "success")
        check_url(all_data)
    except requests.exceptions.RequestException:
        flash("Произошла ошибка при проверке", "danger")
    finally:
        return redirect(url_for("url_show", id=id))
