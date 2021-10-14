/*
 * JavaScript MD5 Test
 * https://github.com/blueimp/JavaScript-MD5
 *
 * Copyright 2011, Sebastian Tschan
 * https://blueimp.net
 *
 * Licensed under the MIT license:
 * https://opensource.org/licenses/MIT
 */

/* global describe, it */

/* eslint-disable strict */

;(function (expect, md5) {
  'use strict'

  describe('MD5 Hex-encoding', function () {
    it('should create a hex-encoded MD5 hash of an ASCII value', function () {
      expect(md5('value')).to.equal('2063c1608d6e0baf80249c42e2be5804')
    })

    it('should create a hex-encoded MD5 hash of an UTF-8 value', function () {
      expect(md5('日本')).to.equal('4dbed2e657457884e67137d3514119b3')
    })
  })

  describe('HMAC-MD5 Hex-encoding', function () {
    it('should create a hex-encoded HMAC-MD5 hash of an ASCII value and key', function () {
      expect(md5('value', 'key')).to.equal('01433efd5f16327ea4b31144572c67f6')
    })

    it('should create a hex-encoded HMAC-MD5 hash of an UTF-8 value and key', function () {
      expect(md5('日本', '日本')).to.equal('c78b8c7357926981cc04740bd3e9d015')
    })
  })

  describe('MD5 raw encoding', function () {
    it('should create a raw MD5 hash of an ASCII value', function () {
      expect(md5('value', null, true)).to.equal(
        ' c\xc1`\x8dn\x0b\xaf\x80$\x9cB\xe2\xbeX\x04'
      )
    })

    it('should create a raw MD5 hash of an UTF-8 value', function () {
      expect(md5('日本', null, true)).to.equal(
        'M\xbe\xd2\xe6WEx\x84\xe6q7\xd3QA\x19\xb3'
      )
    })
  })

  describe('HMAC-MD5 raw encoding', function () {
    it('should create a raw HMAC-MD5 hash of an ASCII value and key', function () {
      expect(md5('value', 'key', true)).to.equal(
        '\x01C>\xfd_\x162~\xa4\xb3\x11DW,g\xf6'
      )
    })

    it('should create a raw HMAC-MD5 hash of an UTF-8 value and key', function () {
      expect(md5('日本', '日本', true)).to.equal(
        '\xc7\x8b\x8csW\x92i\x81\xcc\x04t\x0b\xd3\xe9\xd0\x15'
      )
    })
  })
})((this.chai || require('chai')).expect, this.md5 || require('../js/md5'))
