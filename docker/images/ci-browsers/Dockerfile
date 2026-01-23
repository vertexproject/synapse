# vim:set ft=dockerfile:
ARG CI_BASE_IMAGE

# FIXME add a default argument value here.
FROM ${CI_BASE_IMAGE}

ENV DISPLAY=":99"

COPY docker/images/ci-browsers /build/ci-browsers

RUN /build/ci-browsers/bootstrap.sh

# Use the xvfb entrypoint
LABEL com.circleci.preserve-entrypoint=true
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/sh"]
