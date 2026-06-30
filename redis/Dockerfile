FROM redis:5-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

HEALTHCHECK \
    --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD sh -c 'echo PING | nc localhost 6379' || exit 1

USER redis

EXPOSE 6379

CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]
