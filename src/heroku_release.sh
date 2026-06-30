#!/usr/bin/env bash

# TODO swap from `-Eeo pipefail` to `-Eeuo pipefail` above (after handling all potentially-unset variables)
set -Eeuo pipefail

if [ -n "${PYTHONHOME:-}" ] ; then
    export PATH="${PYTHONHOME}/bin:${PATH}"
fi
if [ -n "${PY_VENV:-}" ] ; then
    export PATH="${PY_VENV}/bin:${PATH}"
fi

if [ -z "${DATABASE_URL:-}" ] ; then
    exit 0
fi

#python -m narra_backend.manage makemigrations

#for fname in narra_backend/api/migrations/*.py ; do
#    echo "=== [ ${fname} ] ==="
#    cat "${fname}"
#    echo "=== === ==="
#done

CLOUDCUBE_URL='' python -m narra_backend.manage migrate
