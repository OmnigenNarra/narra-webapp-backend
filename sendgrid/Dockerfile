FROM python:3.8-alpine

ENV \
    FAKE_SENDGRID_SRV_HOST='' \
    FAKE_SENDGRID_SRV_PORT=18025

COPY fake_sendgrid_server.py /fake_sendgrid_server.py

HEALTHCHECK \
    --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${FAKE_SENDGRID_SRV_PORT} || exit 1

USER nobody

EXPOSE 18025

CMD [ "python", "/fake_sendgrid_server.py" ]
