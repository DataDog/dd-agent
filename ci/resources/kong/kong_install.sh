#!/bin/bash

set -e

pushd $INTEGRATIONS_DIR/kong
wget -O $VOLATILE_DIR/kong.tar.gz https://github.com/Mashape/kong/archive/0.8.1.tar.gz
tar xvzf $VOLATILE_DIR/kong.tar.gz -C . --strip-components=1
mkdir $LUAJIT_DIR/include/$LUA_VERSION/uuid
cp $UUID_DIR/usr/include/uuid/* $LUAJIT_DIR/include/$LUA_VERSION/uuid
cp $UUID_DIR/usr/lib/libuuid* $LUAJIT_DIR/lib
popd
