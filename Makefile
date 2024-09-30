install:
	pip install -r requirements.txt
build:
	./build.sh
dev:
	poetry run flask --app page_analyzerr:app run
lint:
	poetry run flake8 page_analyzerr
PORT ?= 8000
start:
	poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzerr:app
