#!/bin/bash

set -e


pushd $INTEGRATIONS_DIR/kong

wget -O $VOLATILE_DIR/kong.tar.gz https://github.com/Mashape/kong/archive/0.6.0.tar.gz
tar xvzf $VOLATILE_DIR/kong.tar.gz -C . --strip-components=1

mkdir ./util
wget -O $VOLATILE_DIR/util-linux-2.27.tar.gz https://www.kernel.org/pub/linux/utils/util-linux/v2.27/util-linux-2.27.tar.gz
tar xvzf $VOLATILE_DIR/util-linux-2.27.tar.gz -C ./util --strip-components=1
luarocks install lua_uuid UUID_LIBDIR=./util/libuuid/src/

luarocks make kong-*.rockspec
popd