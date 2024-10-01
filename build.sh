#1/usr/bin/env bash

make install && export PATH="/opt/render/project/poetry/bin:$PATH" && psql -a -d "$DATABASE_URL" -f database.sql
