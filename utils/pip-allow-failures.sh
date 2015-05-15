#!/bin/bash

PIP_COMMAND=${PIP_COMMAND:-pip}
PIP_OPTIONS=${PIP_OPTIONS:-}
REQUIREMENTS_FILE=$1

while read dependency; do
    dependency_stripped="$(echo "${dependency}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    # Skip comments
    if [[ $dependency_stripped == \#* ]]; then
        continue
    # Skip blank lines
    elif [ -z "$dependency_stripped" ]; then
        continue
    else
        if $PIP_COMMAND install $PIP_OPTIONS "$dependency_stripped" 2>&1; then
            echo "$dependency_stripped is installed"
        else
            echo "Could not install $dependency_stripped, skipping"
        fi
    fi
done < "$1"
