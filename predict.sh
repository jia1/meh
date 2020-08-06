#!/bin/bash

PROJECT_ROOT=~/meh
cd $PROJECT_ROOT/darknet
./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg darknet19.weights $PROJECT_ROOT/$1
cd $PROJECT_ROOT
