#!/bin/bash

set -e


pushd $INTEGRATIONS_DIR
mkdir $UUID_DIR

curl https://www.kernel.org/pub/linux/utils/util-linux/v2.27/util-linux-2.27.tar.gz | tar xz
pushd util-linux-2.27
./configure \
 --disable-use-tty-group\
 --with-python=2
make
make install DESTDIR=$UUID_DIR
popd

pushd $INTEGRATIONS_DIR/kong
wget -O $VOLATILE_DIR/kong.tar.gz https://github.com/Mashape/kong/archive/0.6.0.tar.gz
tar xvzf $VOLATILE_DIR/kong.tar.gz -C . --strip-components=1
mkdir $LUAJIT_DIR/include/$LUA_VERSION/uuid
cp $UUID_DIR/usr/include/uuid/* $LUAJIT_DIR/include/$LUA_VERSION/uuid
cp $UUID_DIR/usr/lib/libuuid* $LUAJIT_DIR/lib

make dev
cp $TRAVIS_BUILD_DIR/ci/resources/kong/*.yml ./
kong start -c kong_DEVELOPMENT.yml
popd
popd