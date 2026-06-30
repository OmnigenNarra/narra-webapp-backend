#!/usr/bin/env bash

# NOTE: this script assumes the CWD is app's root dir (containing setup.py, requirements.txt et al.)

#set -x
# TODO swap from `-Eeo pipefail` to `-Eeuo pipefail` above (after handling all potentially-unset variables)
set -Eeuo pipefail

if [ -z "${PY_VENV:-}" ] ; then
    export PY_VENV=''
fi
if [ -z "${PYTHONHOME:-}" ] ; then
    export PYTHONHOME=''
fi

if [ -f "${PY_VENV}/bin/activate" ] ; then
    source ${PY_VENV}/bin/activate
fi

if [ -n "${PYTHONHOME}" ] ; then
    export PATH="${PYTHONHOME}/bin:${PATH}"
fi
if [ -n "${PY_VENV}" ] ; then
    export PATH="${PY_VENV}/bin:${PATH}"
fi

COLLECTSTATIC_OPTS="--clear --no-input --no-default-ignore \
    --ignore .* --ignore *~ --ignore LICENSE* --ignore README* \
    --ignore i18n --ignore rest_framework"

case "${1}" in
    django-manage)
        shift
        exec python -m narra_backend.manage "${@}"
        ;;

    django-migrate-db)
        ${0} django-manage makemigrations
        exec ${0} django-manage migrate --database narra_a
        ;;

    django-create-token)
        shift
        exec ${0} django-manage drf_create_token "${@}"
        ;;

    django-createsuperuser)
        shift
        exec ${0} django-manage createsuperuser "${@}"
        ;;

    django-collectstatic)
        set -f
        exec ${0} django-manage collectstatic ${COLLECTSTATIC_OPTS}
        ;;

    django-collectstatic-dev)
        set -f
        exec ${0} django-manage collectstatic --link ${COLLECTSTATIC_OPTS}
        ;;

    django-gunicorn)
        ./heroku_release.sh
        exec ./heroku_web.sh
        ;;

    django-gunicorn-dev)
        ./heroku_release.sh
        shift
        exec ./heroku_web.sh --reload "${@}"
        ;;

    tests)
        # pylint --output-format colorized --load-plugins pylint_django \
        #    --ignore migrations narra_backend tests *.py
        python -m jsonschema -i ./doc/API/examples/package.json \
            ./narra_backend/static/schemas/current.json
        export HTTP_AUTHZ='c29tZTpwYXNz'
        exec py.test --verbose --verbose --doctest-modules --create-db --reuse-db \
            -o cache_dir=/tmp --pep8 narra_backend \
            --cov narra_backend --cov-report term-missing tests
        ;;

    *)
        echo "Unknown command: ${1}"
        ;;
esac

exit 1
