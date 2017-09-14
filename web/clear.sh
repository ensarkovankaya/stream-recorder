#!/bin/sh
if [ -d "logs" ]; then
    rm -r logs/*
fi

if [ -d "media" ]; then
    if [ -d "media/videos" ]; then
        rm -r media/videos
    fi
fi

if [ -d "static/*" ]; then
    rm -r static/*
fi

rm */migrations/0*