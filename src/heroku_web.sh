#!/usr/bin/env bash

# TODO swap from `-Eeo pipefail` to `-Eeuo pipefail` above (after handling all potentially-unset variables)
set -Eeuo pipefail

PRE_EXEC=''
if [ -x 'bin/start-pgbouncer' ] ; then
    PRE_EXEC="bin/start-pgbouncer ${PRE_EXEC}"
fi
if [ -x 'bin/start-nginx' ] ; then
    PRE_EXEC="bin/start-nginx ${PRE_EXEC}"
fi

${PRE_EXEC} gunicorn --config gunicorn_conf.py narra_backend.main:APP --worker-class aiohttp.worker.GunicornWebWorker --enable-stdio-inheritance --log-file - "${@}"
