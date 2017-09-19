FROM python:3.6.2-onbuild
ENV PYTHONUNBUFFERED 1

# Install gettext for Django
RUN apt-get update && \
    apt-get install -y gettext

# FFmpeg Installation

ENV FFMPEG_SOURCES /tmp/ffmpeg_sources
ENV FFMPEG_BUILD /tmp/ffmpeg_build
ENV FFMPEG_BIN /usr/bin

# Install Dependencies
RUN apt-get update && apt-get -y install autoconf automake build-essential libass-dev libfreetype6-dev \
  libsdl2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev \
  libxcb-xfixes0-dev pkg-config texinfo wget zlib1g-dev

# Create Build Directories
RUN mkdir -p $FFMPEG_SOURCES $FFMPEG_BUILD

# Compile Yasm
RUN cd $FFMPEG_SOURCES && \
    wget http://www.tortall.net/projects/yasm/releases/yasm-1.3.0.tar.gz && \
    tar xzvf yasm-1.3.0.tar.gz && \
    cd yasm-1.3.0 && \
    ./configure --prefix="$FFMPEG_BUILD" --bindir="$FFMPEG_BIN" && \
    make && \
    make install

# Compile Nasm
RUN cd $FFMPEG_SOURCES && \
    wget http://www.nasm.us/pub/nasm/releasebuilds/2.13.01/nasm-2.13.01.tar.bz2 && \
    tar xjvf nasm-2.13.01.tar.bz2 && \
    cd nasm-2.13.01 && \
    ./autogen.sh && \
    PATH="$FFMPEG_BIN:$PATH" ./configure --prefix="$FFMPEG_BUILD" --bindir="$FFMPEG_BIN" && \
    PATH="$FFMPEG_BIN:$PATH" make && make install

# Compile libx264
RUN cd $FFMPEG_SOURCES && \
    wget http://download.videolan.org/pub/x264/snapshots/last_x264.tar.bz2 && \
    tar xjvf last_x264.tar.bz2 && \
    cd x264-snapshot* && \
    PATH="$FFMPEG_BIN:$PATH" ./configure --prefix="$FFMPEG_BUILD" --bindir="$FFMPEG_BIN" --enable-static --disable-opencl && \
    PATH="$FFMPEG_BIN:$PATH" make && make install

# Compile libx265
RUN apt-get install -y cmake mercurial && \
    cd $FFMPEG_SOURCES && \
    hg clone https://bitbucket.org/multicoreware/x265 && \
    cd $FFMPEG_SOURCES/x265/build/linux && \
    PATH="$FFMPEG_BIN:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$FFMPEG_BUILD" -DENABLE_SHARED:bool=off ../../source && \
    make && make install

# Compile libfdk-aac
RUN cd $FFMPEG_SOURCES && \
    wget -O fdk-aac.tar.gz https://github.com/mstorsjo/fdk-aac/tarball/master && \
    tar xzvf fdk-aac.tar.gz && \
    cd mstorsjo-fdk-aac* && \
    autoreconf -fiv && \
    ./configure --prefix="$FFMPEG_BUILD" --disable-shared && \
    make && make install

# Compile libmp3lame
RUN cd $FFMPEG_SOURCES && \
    wget http://downloads.sourceforge.net/project/lame/lame/3.99/lame-3.99.5.tar.gz && \
    tar xzvf lame-3.99.5.tar.gz && \
    cd lame-3.99.5 && \
    ./configure --prefix="$FFMPEG_BUILD" --enable-nasm --disable-shared && \
    make && make install

# Compile libopus
RUN cd $FFMPEG_SOURCES && \
    wget https://archive.mozilla.org/pub/opus/opus-1.1.5.tar.gz && \
    tar xzvf opus-1.1.5.tar.gz && \
    cd opus-1.1.5 && \
    ./configure --prefix="$FFMPEG_BUILD" --disable-shared && \
    make && make install

# Compile libvpx
RUN apt-get install -y git && \
    cd $FFMPEG_SOURCES && \
    git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git && \
    cd libvpx && \
    PATH="$FFMPEG_BIN:$PATH" ./configure --prefix="$FFMPEG_BUILD" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth && \
    PATH="$FFMPEG_BIN:$PATH" make && make install

# Compile FFmpeg
RUN cd $FFMPEG_SOURCES && \
    wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
    tar xjvf ffmpeg-snapshot.tar.bz2 && \
    cd ffmpeg && \
    PATH="$FFMPEG_BIN:$PATH" PKG_CONFIG_PATH="$FFMPEG_BUILD/lib/pkgconfig" ./configure \
      --prefix="$FFMPEG_BUILD" \
      --pkg-config-flags="--static" \
      --extra-cflags="-I$FFMPEG_BUILD/include" \
      --extra-ldflags="-L$FFMPEG_BUILD/lib" \
      --bindir="$FFMPEG_BIN" \
      --enable-gpl \
      --enable-libass \
      --enable-libfdk-aac \
      --enable-libfreetype \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libtheora \
      --enable-libvorbis \
      --enable-libvpx \
      --enable-libx264 \
      --enable-libx265 \
      --enable-nonfree && \
    PATH="$FFMPEG_BIN:$PATH" make && \
    make install && \
    hash -r

# Cleaning
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf $FFMPEG_SOURCES $FFMPEG_BUILD