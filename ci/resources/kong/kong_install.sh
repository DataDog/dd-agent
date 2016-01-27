#!/bin/bash

set -e

export LUA_VERSION=luajit-2.1
export CASSANDRA_VERSION=2.2.4
export LUAROCKS_VERSION=2.2.2
export OPENSSL_VERSION=1.0.2e
export OPENRESTY_VERSION=1.9.3.1
export SERF_VERSION=0.7.0
export DNSMASQ_VERSION=2.75
export LUAJIT_DIR=$INTEGRATIONS_DIR/kong/luajit
export LUAROCKS_DIR=$INTEGRATIONS_DIR/kong/luarocks
export OPENRESTY_DIR=$INTEGRATIONS_DIR/kong/openresty
export SERF_DIR=$INTEGRATIONS_DIR/kong/serf
export DNSMASQ_DIR=$INTEGRATIONS_DIR/kong/dnsmasq
export CASSANDRA_HOSTS=127.0.0.1

wget -P .ci/ https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/platform.sh
wget -O - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_lua.sh | bash
wget -O - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_openresty.sh | bash
wget -O - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_serf.sh | bash
wget -O - https://raw.githubusercontent.com/Mashape/kong/feat/invalidations/.ci/setup_dnsmasq.sh | bash

export PATH="$LUAJIT_DIR/bin:$LUAROCKS_DIR/bin:$OPENRESTY_DIR/nginx/sbin:$SERF_DIR:$DNSMASQ_DIR/usr/local/sbin:$PATH"
export LUA_PATH="./?.lua;$LUAROCKS_DIR/share/lua/5.1/?.lua;$LUAROCKS_DIR/share/lua/5.1/?/init.lua;$LUAROCKS_DIR/lib/lua/5.1/?.lua;$LUA_PATH"
export LUA_CPATH="./?.so;$LUAROCKS_DIR/lib/lua/5.1/?.so;$LUA_CPATH"

wget -O kong.tar.gz https://github.com/Mashape/kong/archive/0.6.0.tar.gz
tar xzf kong.tar.gz

luarocks make ./kong-0.6.0/kong-*.rockspec