#!/bin/bash

set -e


pushd $INTEGRATIONS_DIR/kong

wget -O $VOLATILE_DIR/kong.tar.gz https://github.com/Mashape/kong/archive/0.6.0.tar.gz
tar xvzf $VOLATILE_DIR/kong.tar.gz -C . --strip-components=1

echo $PATH
echo $LUAROCKS_DIR
echo $LUA_CPATH
echo $LUA_PATH

mkdir ./util
wget -O $VOLATILE_DIR/util-linux-2.27.tar.gz https://www.kernel.org/pub/linux/utils/util-linux/v2.27/util-linux-2.27.tar.gz
tar xvzf $VOLATILE_DIR/util-linux-2.27.tar.gz -C ./util --strip-components=1

$LUAROCKS_DIR/bin/luarocks install lua_uuid UUID_LIBDIR=$INTEGRATIONS_DIR/kong/util/libuuid/src/ LUA_INCDIR=$INTEGRATIONS_DIR/kong/util/libuuid/include

$LUAROCKS_DIR/bin/luarocks make kong-*.rockspec
popd