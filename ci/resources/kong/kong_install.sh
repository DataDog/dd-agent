#!/bin/bash

set -e

pwd
echo $INTEGRATIONS_DIR
mkdir $INTEGRATIONS_DIR/luajit
mkdir $INTEGRATIONS_DIR/luarocks
mkdir $INTEGRATIONS_DIR/openresty
mkdir $INTEGRATIONS_DIR/serf
mkdir $INTEGRATIONS_DIR/dnsmasq

export LUA_VERSION=luajit-2.1
export CASSANDRA_VERSION=2.2.4
export LUAROCKS_VERSION=2.2.2
export OPENSSL_VERSION=1.0.2e
export OPENRESTY_VERSION=1.9.3.1
export SERF_VERSION=0.7.0
export DNSMASQ_VERSION=2.75
export LUAJIT_DIR=$INTEGRATIONS_DIR/luajit
export LUAROCKS_DIR=$INTEGRATIONS_DIR/luarocks
export OPENRESTY_DIR=$INTEGRATIONS_DIR/openresty
export SERF_DIR=$INTEGRATIONS_DIR/serf
export DNSMASQ_DIR=$INTEGRATIONS_DIR/dnsmasq
export CASSANDRA_HOSTS=127.0.0.1

mkdir $INTEGRATIONS_DIR/.ci
pushd $INTEGRATIONS_DIR

wget -P $INTEGRATIONS_DIR/.ci/ https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/platform.sh
wget -P $INTEGRATIONS_DIR/ - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_lua.sh | bash
wget -P $INTEGRATIONS_DIR/ - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_openresty.sh | bash
wget -P $INTEGRATIONS_DIR/ - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_serf.sh | bash
wget -P $INTEGRATIONS_DIR/ - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_dnsmasq.sh | bash



export PATH="$LUAJIT_DIR/bin:$LUAROCKS_DIR/bin:$OPENRESTY_DIR/nginx/sbin:$SERF_DIR:$DNSMASQ_DIR/usr/local/sbin:$PATH"
export LUA_PATH="./?.lua;$LUAROCKS_DIR/share/lua/5.1/?.lua;$LUAROCKS_DIR/share/lua/5.1/?/init.lua;$LUAROCKS_DIR/lib/lua/5.1/?.lua;$LUA_PATH"
export LUA_CPATH="./?.so;$LUAROCKS_DIR/lib/lua/5.1/?.so;$LUA_CPATH"

wget -O $INTEGRATIONS_DIR/kong/kong.tar.gz https://github.com/Mashape/kong/archive/0.6.0.tar.gz
tar xvzf $INTEGRATIONS_DIR/kong/kong.tar.gz -C $INTEGRATIONS_DIR/kong/ --strip-components=1

mkdir $INTEGRATIONS_DIR/kong/util
wget -O $INTEGRATIONS_DIR/kong/util-linux-2.27.tar.gz https://www.kernel.org/pub/linux/utils/util-linux/v2.27/util-linux-2.27.tar.gz
tar xvzf $INTEGRATIONS_DIR/kong/util-linux-2.27.tar.gz -C $INTEGRATIONS_DIR/kong/util --strip-components=1
luarocks install lua_uuid UUID_LIBDIR=$INTEGRATIONS_DIR/kong/util/libuuid/src/

pwd
pushd $INTEGRATIONS_DIR/kong
luarocks make kong-*.rockspec
popd
popd