#!/bin/bash

#
# Run setup.sh <python binary 1> <python binary 2> ... <python binary N> to set up
# virtual environments for running tests.  For example:
#
# ./setup.sh python2.6 python2.7 python3.2 pypy-1.6
#

BASE_DIR=$(dirname $0)

if [[ -z $* ]]; then
  echo "You should input an interpreter."
  exit 1
fi

for bin in $*; do
  cat <<EOF | $bin - > $BASE_DIR/.target
import sys
subversion = getattr(sys, 'subversion', ['CPython'])[0]
print(".virtualenv-%s-%s.%s"%(subversion,sys.version_info[0],sys.version_info[1]))
EOF
  TARGET=$BASE_DIR/$(cat .target)
  echo Installing into $TARGET
  if test -e $TARGET; then
    echo Cleaning original virtualenv
    rm -rf $TARGET
  fi
  python -m virtualenv -p $bin $TARGET
  pushd $TARGET
    source bin/activate
    pip install pytest pytest-cov pytest-xdist
    deactivate
  popd
done
rm -f $BASE_DIR/.target
