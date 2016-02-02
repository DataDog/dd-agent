#!/bin/bash

# A script for setting up environment for travis-ci testing.
# Sets up Lua and Luarocks.
# LUA must be "lua5.1", "lua5.2" or "luajit".
# luajit2.0 - master v2.0
# luajit2.1 - master v2.1

set -e


pushd $INTEGRATIONS_DIR/


############
# Lua/LuaJIT
############

mkdir -p $LUAJIT_DIR

if [ ! "$(ls -A $LUAJIT_DIR)" ]; then
  LUAJIT_BASE="LuaJIT"
  git clone https://github.com/luajit/luajit $LUAJIT_BASE
  pushd $LUAJIT_BASE

  if [ "$LUAJIT_VERSION" == "2.1" ]; then
    git checkout v2.1
    perl -i -pe 's/INSTALL_TNAME=.+/INSTALL_TNAME= luajit/' Makefile
  else
    git checkout v2.0.4
  fi

  make
  make install PREFIX=$LUAJIT_DIR
  popd
  
  ln -sf $LUAJIT_DIR/bin/luajit $LUAJIT_DIR/bin/lua
  rm -rf $LUAJIT_BASE
else
   echo "Lua found from cache at $LUAJIT_DIR"
fi

##########
# Luarocks
##########

mkdir -p $LUAROCKS_DIR
if [ ! "$(ls -A $LUAROCKS_DIR)" ]; then
  LUAROCKS_BASE=luarocks-$LUAROCKS_VERSION
  git clone https://github.com/keplerproject/luarocks.git $LUAROCKS_BASE

  pushd $LUAROCKS_BASE
  git checkout v$LUAROCKS_VERSION
  ./configure \
    --prefix=$LUAROCKS_DIR \
    --with-lua-bin=$LUAJIT_DIR/bin \
    --with-lua-include=$LUAJIT_DIR/include/luajit-$LUAJIT_VERSION
  make build
  make install
  popd

  rm -rf $LUAROCKS_BASE
else
  echo "Luarocks found from cache at $LUAROCKS_DIR"
fi

popd