# Copyright(C) Venidera Research & Development, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Rafael Giordano Vieira <rafael@venidera.com>

FROM python:3.8-alpine
# Capturing default arguments
ARG API_PORT
ARG ALLOWED_EMAILS
ARG API_URL
ARG APP_URL
ARG ATLAS_DB
ARG COOKIE_SECRET
ARG CVREQ_TIMELIMIT
ARG CVSERVER_URL
ARG CVSERVER_URL_IDENTIFICATION
ARG CVSERVER_URL_RESULTS
ARG CV_APIKEY
ARG CV_PASSWORD
ARG CV_USERNAME
ARG EMAIL_FROM
ARG MONGODB_URI
ARG MONGOLAB_URI
ARG REDISCLOUD_URL
ARG REDIS_URL
ARG S3_ACCESS_KEY
ARG S3_BUCKET
ARG S3_SECRET_KEY
ARG S3_URL
ARG S3_URL_EXPIRE_SECONDS
ARG SMTP_PASSWORD
ARG SMTP_PORT
ARG SMTP_SERVER
ARG SMTP_USERNAME
ARG TOKEN_SECRET
ARG TZ
# Setting environment variables
ENV API_PORT=${API_PORT}
ENV ALLOWED_EMAILS=${ALLOWED_EMAILS}
ENV API_URL=${API_URL}
ENV APP_URL=${APP_URL}
ENV ATLAS_DB=${ATLAS_DB}
ENV COOKIE_SECRET=${COOKIE_SECRET}
ENV CVREQ_TIMELIMIT=${CVREQ_TIMELIMIT}
ENV CVSERVER_URL=${CVSERVER_URL}
ENV CVSERVER_URL_IDENTIFICATION=${CVSERVER_URL_IDENTIFICATION}
ENV CVSERVER_URL_RESULTS=${CVSERVER_URL_RESULTS}
ENV CV_APIKEY=${CV_APIKEY}
ENV CV_PASSWORD=${CV_PASSWORD}
ENV CV_USERNAME=${CV_USERNAME}
ENV EMAIL_FROM=${EMAIL_FROM}
ENV MONGODB_URI=${MONGODB_URI}
ENV MONGOLAB_URI=${MONGOLAB_URI}
ENV REDISCLOUD_URL=${REDISCLOUD_URL}
ENV REDIS_URL=${REDIS_URL}
ENV S3_ACCESS_KEY=${S3_ACCESS_KEY}
ENV S3_BUCKET=${S3_BUCKET}
ENV S3_SECRET_KEY=${S3_SECRET_KEY}
ENV S3_URL=${S3_URL}
ENV S3_URL_EXPIRE_SECONDS=${S3_URL_EXPIRE_SECONDS}
ENV SMTP_PASSWORD=${SMTP_PASSWORD}
ENV SMTP_PORT=${SMTP_PORT}
ENV SMTP_SERVER=${SMTP_SERVER}
ENV SMTP_USERNAME=${SMTP_USERNAME}
ENV TOKEN_SECRET=${TOKEN_SECRET}
ENV TZ=${TZ}

# Creating base image
RUN apk update && apk upgrade && \
    # Installing common packages
    apk add \
        openssl \
        vim \
        bash \
        gfortran \
        curl \
        gcc \
        g++ \
        libxml2-dev \
        libxslt-dev \
        libgcc \
        linux-headers \
        musl-dev \
        libc-dev \
        python3-dev \
        libffi-dev \
        curl-dev \
        build-base \
        py-pip \
        zlib \
        tzdata \
        zlib-dev \
        lapack-dev \
        jpeg-dev \
        freetype-dev \
        lcms2-dev \
        openjpeg-dev \
        tiff-dev \
        tk-dev \
        tcl-dev \
        openssl-dev && \
    rm -rf /tmp/* /var/cache/apk/*
# Copying local repository
COPY . /linc-api
# Updating pip and installing the dependencies
RUN pip install --upgrade -r /linc-api/requirements.txt pip setuptools wheel
# Exposing port
EXPOSE ${API_PORT}
# Creating working directory
WORKDIR /linc-api
# Running execution command
CMD ["/bin/bash", "-c", "python /linc-api/app/linc-api.py --port=${API_PORT}"]
