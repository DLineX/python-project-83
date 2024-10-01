#1/usr/bin/env bash

make install && psql -a -d $DATABASE_URL -f database.sql && export PATH="/opt/render/project/poetry/bin:$PATH"
