#! /bin/bash

set -e

npm install --dev 
npm run test
npm run test:coverage
