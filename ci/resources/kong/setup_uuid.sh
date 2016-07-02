#!/bin/bash

set -e


pushd $INTEGRATIONS_DIR
mkdir $UUID_DIR

curl https://www.kernel.org/pub/linux/utils/util-linux/v2.27/util-linux-2.27.tar.gz | tar xz
echo $TRAVIS_PYTHON_VERSION
pushd util-linux-2.27
./configure \
 --disable-use-tty-group\
 PYTHON_CFLAGS="-I/usr/include/python$TRAVIS_PYTHON_VERSION"
make
make install DESTDIR=$UUID_DIR
popd
popd