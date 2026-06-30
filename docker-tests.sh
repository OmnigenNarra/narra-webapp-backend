#!/usr/bin/env bash

#set -x
# TODO swap from `-Eeo pipefail` to `-Eeuo pipefail` above (after handling all potentially-unset variables)
set -Eeuo pipefail

cd "`dirname \"${0}\"`"

docker-compose build
docker-compose --file docker-compose.yml --file docker-compose-tests.yml up --force-recreate --build --remove-orphans --renew-anon-volumes --abort-on-container-exit
