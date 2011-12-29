#!/bin/bash

#
# Run setup.sh <python binary 1> <python binary 2> ... <python binary N> to set up
# virtual environments for running tests.  For example:
#
# ./setup.sh python2.6 python2.7 python3.2 pypy-1.6
#

MY_DIR=$(dirname $0)
BASE_DIR=$MY_DIR

mkdir .virtualenv.cache
pushd .virtualenv.cache
  if ! test -f virtualenv-1.7.tar.gz; then
    wget http://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.7.tar.gz
  fi
  gzip -cd virtualenv-1.7.tar.gz | tar -xvf -
popd

for bin in $*; do
  cat <<EOF | $bin - > .target
import sys
print(".virtualenv-%s-%s.%s"%(sys.subversion[0],sys.version_info[0],sys.version_info[1]))
EOF
  TARGET=$BASE_DIR/$(cat .target)
  echo Installing into $TARGET
  if test -e $TARGET; then
    echo Cleaning original virtualenv
    rm -rf $TARGET
  fi
  $bin .virtualenv.cache/virtualenv-1.7/virtualenv.py --distribute $TARGET
  $TARGET/bin/pip install --download-cache=.virtualenv.cache pytest pytest-cov pytest-xdist
done
rm -f .target
