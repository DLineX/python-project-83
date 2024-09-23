from flask import Flask
import os
import psycopg2
import requests
from flask import render_template, flash, redirect, url_for

from dotenv import load_dotenv
from urllib.parse import urlparse


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


def find_url(id):
    with connect().cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM urls WHERE id=%(id)s;
            """,
            {"id": id}
        )
        url_id, name, created_at = cursor.fetchone()
        return {
            "id": url_id,
            "name": name,
            "created_at": created_at
        }


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
