install:
	poetry install
dev:
	poetry run flask --app page_analyzer:app run