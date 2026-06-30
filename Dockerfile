FROM heroku/heroku:18-build AS build

ARG STACK
ARG APPLICATION
ARG REDIS_URL
ARG DATABASE_URL
ARG DJANGO_SECRET_KEY

WORKDIR ${APPLICATION}

# BUILDPACKS:
# - https://github.com/soutys/custom-ssh-key-buildpack.git
# - https://github.com/heroku/heroku-buildpack-apt
# - https://bitbucket.org/to_reforge/narra-validators-heroku-buildpack
# - https://github.com/soutys/heroku-buildpack-nginx.git#brotli
# - https://github.com/heroku/heroku-buildpack-pgbouncer.git
# - heroku/python

RUN \
    git clone "https://github.com/soutys/custom-ssh-key-buildpack" /tmp/buildpack/custom-ssh-key && \
    cd /tmp/buildpack/custom-ssh-key && \
    ./bin/compile ${APPLICATION} /tmp/build_cache /tmp/env

COPY narra-validators-heroku-buildpack /tmp/buildpack/narra-validators

RUN \
    cd /tmp/buildpack/narra-validators && \
    ./bin/compile ${APPLICATION} /tmp/build_cache /tmp/env

RUN \
    git clone --branch brotli "https://github.com/soutys/heroku-buildpack-nginx" /tmp/buildpack/nginx && \
    cd /tmp/buildpack/nginx && \
    ./bin/compile ${APPLICATION} /tmp/build_cache /tmp/env && \
    cp /tmp/buildpack/nginx/bin/nginx-${STACK} bin/nginx

RUN \
    mkdir -p /tmp/buildpack/pgbouncer /tmp/buildpack/python /tmp/buildpack/nginx /tmp/build_cache /tmp/env

RUN \
    git clone "https://github.com/heroku/heroku-buildpack-pgbouncer" /tmp/buildpack/pgbouncer && \
    cd /tmp/buildpack/pgbouncer && \
    echo "pgbouncer in-place upgrade starts..." && \
    export PGBOUNCER_VERSION_OLD='pgbouncer-1.8.1-heroku' && \
    export PGBOUNCER_VERSION_NEW='pgbouncer-1.10.0' && \
    curl -L -O https://github.com/pgbouncer/pgbouncer/releases/download/pgbouncer_1_10_0/${PGBOUNCER_VERSION_NEW}.tar.gz && \
    tar xzf ${PGBOUNCER_VERSION_NEW}.tar.gz && \
    cd ${PGBOUNCER_VERSION_NEW} && \
    apt-get update && \
    apt-get install -y libudns-dev && \
    mkdir _build && \
    ./autogen.sh && \
    ./configure --prefix=`pwd`/_build --with-udns && \
    make install && \
    tar -C _build -czf ${PGBOUNCER_VERSION_OLD}.tgz . && \
    mv -f ${PGBOUNCER_VERSION_OLD}.tgz ../ && \
    cd .. && \
    rm -rf ${PGBOUNCER_VERSION_NEW}* && \
    echo "pgbouncer in-place upgrade end." && \
    ./bin/compile ${APPLICATION} /tmp/build_cache /tmp/env && \
    bash ./bin/gen-pgbouncer-conf.sh

COPY src ${APPLICATION}

RUN \
    apt-get update && \
    apt-get install -y `cat Aptfile | tr "\n" " "`

RUN \
    cd /tmp/buildpack/python && \
    curl -L -O "https://codon-buildpacks.s3.amazonaws.com/buildpacks/heroku/python.tgz" && \
    tar xzf python.tgz && \
    DEBUG_COLLECTSTATIC=1 ./bin/compile ${APPLICATION} /tmp/build_cache /tmp/env

FROM heroku/heroku:18 AS runtime

ARG STACK
ARG APPLICATION
ARG REDIS_URL
ARG DATABASE_URL
ARG DJANGO_SECRET_KEY

ENV \
    PORT=8000 \
    EXP_HTTPS_PORT=8443 \
    HOME=${APPLICATION} \
    HEROKU_USER=app

WORKDIR ${APPLICATION}

COPY --from=build ${APPLICATION} ${APPLICATION}

COPY --from=build /etc/ld.so.conf.d /etc/ld.so.conf.d

RUN \
    useradd --home-dir ${APPLICATION} ${HEROKU_USER}

RUN \
    chown -R ${HEROKU_USER}: ${APPLICATION}

RUN \
    apt-get update && \
    apt-get install -y libudns0 `cat Aptfile | tr "\n" " "`

USER ${HEROKU_USER}

ENV \
    PATH=${APPLICATION}/.heroku/python/bin:${PATH} \
    LD_LIBRARY_PATH=${APPLICATION}/.heroku/vendor/lib:${APPLICATION}/.heroku/python/lib \
    LIBRARY_PATH=${APPLICATION}/.heroku/vendor/lib:${APPLICATION}/.heroku/python/lib \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=true \
    PYTHONHOME=${APPLICATION}/.heroku/python \
    PYTHONPATH=${APPLICATION} \
    GUNICORN_CMD_ARGS="--access-logfile -" \
    STATIC_ROOT=${APPLICATION}/static \
    MEDIA_ROOT=${APPLICATION}/media

ENV \
    REDIS_URL=${REDIS_URL} \
    DATABASE_URL=${DATABASE_URL} \
    DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}

RUN \
    rm -rf ${STATIC_ROOT} && \
    ${PYTHONHOME}/bin/pip install --no-cache-dir --upgrade pip && \
    ${PYTHONHOME}/bin/pip install --no-cache-dir . && \
    ${PYTHONHOME}/bin/python -m compileall narra_backend

COPY docker-entrypoint.sh /_run

RUN /_run django-collectstatic-dev

HEALTHCHECK \
    --interval=3m14s --timeout=10s --start-period=42s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

ENTRYPOINT ["/_run"]

EXPOSE ${PORT}

CMD ["django-gunicorn-dev"]
