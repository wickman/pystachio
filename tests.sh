#!/bin/bash

for py in .virtualenv-*/bin/python; do
  $py setup.py test
done
