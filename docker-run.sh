#!/usr/bin/env bash

cd "`dirname \"${0}\"`"

docker-compose up --force-recreate --build --remove-orphans --renew-anon-volumes --abort-on-container-exit "${@}"
