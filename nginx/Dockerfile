FROM nginx:1.16-alpine

ENV \
    PORT=8000 \
    EXP_HTTP_PORT=8080 \
    EXP_HTTPS_PORT=8443 \
    LANG=C.UTF-8

WORKDIR /var/empty

COPY nginx.conf dhparam.pem /etc/nginx/

COPY site_ssl.crt site_ssl.key /etc/nginx/ssl_certs/

COPY site.conf.template /etc/nginx/conf.d/

COPY site_commons.conf.template /etc/nginx/

RUN \
    envsubst '${PORT}' < /etc/nginx/site_commons.conf.template > /etc/nginx/site_commons.conf && \
    envsubst '${EXP_HTTP_PORT} ${EXP_HTTPS_PORT}' < /etc/nginx/conf.d/site.conf.template > /etc/nginx/conf.d/default.conf

HEALTHCHECK \
    --interval=3m14s --timeout=10s --start-period=42s --retries=3 \
    CMD curl -f http://localhost:${EXP_HTTP_PORT}/ || exit 1

EXPOSE ${EXP_HTTP_PORT} ${EXP_HTTPS_PORT}

ENTRYPOINT ["nginx"]

CMD ["-g", "daemon off;"]
