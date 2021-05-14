#!/bin/bash

if [ -z "$TEST_SERVER_URL" ];
then
    echo "The test server url is not set !"
    exit 1
fi

if [ -z "$TEST_GIFT_VALUE" ];
then
    echo "The test gift value is not set !"
    exit 1
fi

if [ -z "$TEST_TOKEN_SYMBOL" ];
then
    echo "The test token symbol is not set !"
    exit 1
fi

PYTHONPATH=. tavern-ci test_accounts.tavern.yaml --debug -vv --log-level debug -s --log-cli-level debug
