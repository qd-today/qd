#!/bin/sh
cd "$(dirname "$0")/.."
cp node_modules/chai/chai.js test/vendor/
cp node_modules/mocha/mocha.js test/vendor/
cp node_modules/mocha/mocha.css test/vendor/
