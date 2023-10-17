FROM python:3.11-slim

WORKDIR /tmp
COPY ./requirements.txt /tmp/

RUN pip install -r requirements.txt \
        && rm -rf /tmp/requirements.txt \
        && rm -rf /root/.cache

ENV MYPY_FORCE_TERMINAL_WIDTH=200

USER nobody
CMD ["mypy"]
