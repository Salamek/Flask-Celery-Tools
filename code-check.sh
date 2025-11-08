#!/bin/bash
set -e

ruff check .
mypy .
BROKER=sqlite RESULT=sqlite LOCK=sqlite pytest .