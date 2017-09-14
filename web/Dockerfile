FROM python:3.6.2-onbuild
ENV PYTHONUNBUFFERED 1

# Install FFmpeg
RUN echo 'deb http://ftp.debian.org/debian jessie-backports main' >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y ffmpeg gettext && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*