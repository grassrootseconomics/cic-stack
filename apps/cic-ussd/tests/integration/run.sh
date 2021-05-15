#!/bin/bash
PYTHONPATH=. tavern-ci test_accounts.tavern.yaml --debug -vv --log-level debug -s --log-cli-level debug
