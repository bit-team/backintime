#!/bin/bash

VER=`cat VERSION`

tar cfz backintime-$VER.tar.gz AUTHORS CHANGES LICENSE TODO README TRANSLATIONS VERSION *.sh common gnome kde4 notify

