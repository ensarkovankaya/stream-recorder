FROM python:3.6.2-onbuild
ENV PYTHONUNBUFFERED 1

# Install gettext for Django
RUN apt-get update && \
    apt-get install -y gettext

# FFmpeg Installation
ENV FFMPEG_BUILD_FROM_SOURCE false
ENV FFMPEG_SOURCES /tmp/ffmpeg_sources
ENV FFMPEG_BUILD /tmp/ffmpeg_build
ENV FFMPEG_BIN /usr/bin

# Install Dependencies
RUN build_ffmpeg.sh

# Cleaning
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf $FFMPEG_SOURCES $FFMPEG_BUILD