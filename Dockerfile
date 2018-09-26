FROM python:3.6-alpine

#Timezone setting
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

#App Related
RUN apk add            \ 
        postgresql-dev \
        gcc            \
        python3-dev    \
        musl-dev       \
  && addgroup -g 501 leantaas \
  && adduser -G leantaas -u 501 -D leantaas

WORKDIR /opt/leantaas

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip \
  && pip install -r requirements.txt

COPY goose goose
COPY docker_start_up docker_start_up

RUN chown -R leantaas:leantaas /opt/leantaas \
 && chmod +x docker_start_up

USER leantaas

VOLUME /opt/leantaas/migrations
CMD [ "./docker_start_up" ]
