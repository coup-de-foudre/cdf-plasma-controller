FROM themattrix/tox-base

MAINTAINER Mike McCoy michael.b.mccoy@gmail.com

COPY install-prereqs*.sh requirements*.txt tox.ini /app/
COPY vendor /app/vendor
COPY plasma /app/plasma
COPY tests /app/tests
RUN bash -c " \
    if [ -f '/app/install-prereqs.sh' ]; then \
        bash /app/install-prereqs.sh; \
    fi"
