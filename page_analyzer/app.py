from flask import Flask
import os
import requests
from flask import (render_template, flash, request,
                   redirect, url_for, get_flashed_messages)

from dotenv import load_dotenv
import validators
from .db import (add_url, find_url, exists_url, all_urls,
                 all_checks, check_url, beautiful_soup, normalize)


load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
app = Flask(__name__)
app.secret_key = SECRET_KEY


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
            messages=get_flashed_messages(with_categories=True),
            url=url
        ), 422
    url = normalize(url)
    url_found = exists_url(url)
    if url_found:
        flash("Страница уже существует", "info")
        id = url_found.id
        return redirect(url_for('url_show', id=id))
    else:
        id = add_url(url)
        flash("Страница успешно добавлена", "success")
        return redirect(url_for('url_show', id=id.id))


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


@app.post('/urls/<int:id>/checks')
def url_check(id):
    url = find_url(id)
    try:
        response = requests.get(url.name)
        response.raise_for_status()
        all_data = beautiful_soup(response.text)
        all_data['status_code'] = response.status_code
        all_data['url_id'] = id
        flash("Страница успешно проверена", "success")
        check_url(all_data)
    except requests.exceptions.RequestException:
        flash("Произошла ошибка при проверке", "danger")
    finally:
        return redirect(url_for("url_show", id=id))
