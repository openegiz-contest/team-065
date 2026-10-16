# Kyzyl-Tas Mine UI - static SPA served by nginx.
#
# The production bundle is pre-built and committed at mine/ui/dist/, so starting
# the stack needs no `npm install` and no network for the UI. This
# Dockerfile does not run a build step - it only copies the already-built
# dist/ into the nginx webroot.
#
# Do NOT add an nginx.conf here: the reverse-proxy config (Ditto/InfluxDB
# same-origin proxying) is supplied and mounted at runtime
# by deploy/compose/mine.yml from deploy/compose/mine-ui/nginx.conf.template,
# which overrides anything placed at /etc/nginx/conf.d here.
FROM nginx:1.25-alpine

COPY dist/ /usr/share/nginx/html/

EXPOSE 80
