Narra backend
=============
TBA


Documentation
-------------
Created in RAML_ (embedded `JSON Schema`_ ***draft-07***), preview with raml2html_


API
~~~
.. code::

    source ./.venv/bin/activate
    python -m jsonschema -i doc/API/examples/package.json \
        src/narra_backend/static/schemas/current.json && \
    raml2html doc/API/api.raml > doc/API/api.html


Testing
~~~~~~~
.. code::

    # console #1 - supporting services (see 'Pre-setup')
    # console #2 - webserver (see 'Standalone dev')
    # console #3
    ./docker-entrypoint.sh django-manage docs_validate -v 3 -r src/doc/API/api.raml

.. _`JSON Schema`: https://json-schema.org/
.. _RAML: https://raml.org/
.. _raml2html: https://github.com/raml2html/


Pre-setup
---------
.. code::

    python3 -m venv ./.venv
    source ./.venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade docker-compose
    ./docker-run.sh postgres redis sendgrid


JSONs fixing
------------
.. code::

    cd src ; ../jsons_fix.py ; cd ..
    ./packages_validate.py \
        ./examples/package*.json \
        ./src/doc/API/examples/package{-4*,}.json \
        ./src/tests/_data/migrations/package*.json \
        ./src/tests/_data/package*.json

Tests
-----

Standalone
~~~~~~~~~~
.. code::

    export AUTHS_DIR=`pwd`/test_auths
    export DATABASE_URL=postgres://narra_user:foobarpass@localhost:5432/narra
    export REDIS_URL=redis://:foobarpass@localhost:6379
    export DJANGO_SETTINGS_MODULE=narra_backend.settings
    export PY_VENV="${VIRTUAL_ENV}"
    export PORT=8000
    export USE_JSONSCHEMA=1
    export FAKE_SENDGRID_SRV_PORT=18025
    mkdir -p "${AUTHS_DIR}"
    dd if=/dev/urandom of="${AUTHS_DIR}/secret_key.dat" bs=64 count=1
    pip install --upgrade --requirement ./src/test_requirements.txt
    ./docker-entrypoint.sh django-collectstatic-dev
    cd src ; ../docker-entrypoint.sh tests ; cd -


Docker(-compose) (linux)
~~~~~~~~~~~~~~~~~~~~~~~~
.. code::

    mkdir media
    sudo chgrp -R nogroup media
    # required files:
    #   nginx/dhparam.pem
    #   nginx/site_ssl.crt
    #   nginx/site_ssl.key
    #   postgres/narra_db_passwd.secret
    #   redis/redis.conf
    ./docker-tests.sh


Setup
-----

Standalone dev
~~~~~~~~~~~~~~
.. code::

    export AUTHS_DIR=`pwd`/auths
    export DATABASE_URL=postgres://narra_user:foobarpass@localhost:5432/narra
    export REDIS_URL=redis://:foobarpass@localhost:6379
    export DJANGO_SETTINGS_MODULE=narra_backend.settings
    export PY_VENV="${VIRTUAL_ENV}"
    export PORT=8000
    mkdir -p "${AUTHS_DIR}"
    dd if=/dev/urandom of="${AUTHS_DIR}/secret_key.dat" bs=64 count=1
    
    cd ./src/
    python ./setup.py develop
    cd -
    ./docker-entrypoint.sh django-migrate-db
    ./docker-entrypoint.sh django-createsuperuser
    # ./docker-entrypoint.sh django-create-token ...
    ./docker-entrypoint.sh django-collectstatic-dev
    # cd src ; ../docker-entrypoint.sh tests ; cd ..
    cd src ; ../docker-entrypoint.sh django-gunicorn-dev --bind 127.0.0.1:${PORT} ; cd ..
    # http://localhost:8000/admin/


Docker(-compose) dev (linux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code::

    ./docker-run.sh
    
    docker exec -it narra-backend /_run django-migrate-db
    docker exec -it narra-backend /_run django-createsuperuser
    # docker exec -it narra-backend /_run django-create-token ...


Heroku prod
~~~~~~~~~~~
.. code::

    export DJANGO_SETTINGS_MODULE=narra_backend.settings
    export DJANGO_SECRET_KEY='...(your django SECRET_KEY value)...'
    export SENDGRID_API_KEY='...(your SendGrid API key value)...'
    export SENTRY_DSN='...(your Sentry.io DSN)...'
    
    heroku apps:create narra-backend-dev
    heroku git:remote --app narra-backend-dev
    
    heroku buildpacks:clear
    heroku buildpacks:add 'https://github.com/heroku/heroku-buildpack-apt'
    heroku buildpacks:add 'https://github.com/soutys/custom-ssh-key-buildpack'
    heroku buildpacks:add 'https://github.com/soutys/heroku-private-buildpacks'
    heroku buildpacks:add 'https://github.com/soutys/heroku-buildpack-nginx.git#brotli'
    heroku buildpacks:add 'https://github.com/heroku/heroku-buildpack-pgbouncer.git'
    heroku buildpacks:add 'heroku/python'
    
    heroku addons:create cloudcube:free # sets CLOUDCUBE_* envs
    heroku addons:create heroku-postgresql:hobby-dev # sets DATABASE_URL env
    heroku addons:create heroku-redis:hobby-dev # sets REDIS_URL env
    
    export DATABASE_URL="`heroku config:get DATABASE_URL`"
    export REDIS_URL="`heroku config:get REDIS_URL`"
    heroku config:set CUSTOM_SSH_KEY="$(base64 -w 0 ${AUTHS_DIR}/narra_private_repos.pem)"
    heroku config:set CUSTOM_SSH_KEY_HOSTS=bitbucket.org
    heroku config:set SENDGRID_API_KEY="${SENDGRID_API_KEY}"
    heroku config:set SENTRY_DSN="${SENTRY_DSN}"
    heroku config:set DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"
    heroku config:set DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}"
    # heroku config:set DEBUG_COLLECTSTATIC=1
    heroku config:set USE_JSONSCHEMA=1
    
    ./docker-entrypoint.sh django-migrate-db
    ./docker-entrypoint.sh django-createsuperuser
    # ./docker-entrypoint.sh django-create-token ...
    
    git subtree push --prefix src heroku master
    heroku ps:scale web=1
