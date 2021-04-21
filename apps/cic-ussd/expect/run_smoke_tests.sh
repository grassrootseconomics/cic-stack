#!/bin/bash

if [ -z "$TEST_SERVER_URL" ];
then
    echo "The test server url is not set !"
    exit 1
fi

pyresttest "$TEST_SERVER_URL" ./test_suite.yml --log debug