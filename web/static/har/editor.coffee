# vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-01 11:02:45

define (require, exports, module) ->
  require '/static/har/contenteditable'
  require '/static/har/upload_ctrl'
  require '/static/har/entry_list'
  require '/static/har/entry_editor'

  # contentedit-wrapper
  $(document).on('click', '.contentedit-wrapper', (ev) ->
    editable = $(this).hide().next('[contenteditable]').show().focus()
  )
  $(document).on('blur', '.contentedit-wrapper + [contenteditable]', (ev) ->
    $(this).hide().prev('.contentedit-wrapper').show()
  )
  $(document).on('focus', '[contenteditable]', (ev) ->
    if this.childNodes[0]
      range = document.createRange()
      sel = window.getSelection()
      range.setStartBefore(this.childNodes[0])
      range.setEndAfter(this)
      sel.removeAllRanges()
      sel.addRange(range)
  )

  $(() ->
    $('[data-toggle=get-cookie][disabled]').attr('disabled', false)
  )

  # get cookie helper
  cookie_input = null
  $(document).on('click', "[data-toggle=get-cookie]", (ev) ->
    $this = $(this)
    if $this.attr('disabled')
      return
    cookie_input = angular.element($this.parent().find('input'))

    if $('body').attr('get-cookie') is undefined
      # alert('尚未安装GetCookie插件，请安装插件或手动获取！')
      # $this.attr('href', 'https://chrome.google.com/webstore/detail/cookies-get-assistant/ljjpkibacifkfolehlgaolibbnlapkme').attr('target', '_blank')
      return
  )
  window.addEventListener("message", (ev) ->
    if event.origin != window.location.origin
      return

    cookie = ev.data
    cookie_str = ""
    for key, value of cookie
      cookie_str += key + '=' + value + '; '
    if cookie_str == ''
      # alert('没有获得cookie，您是否已经登录？')
      return
    cookie_input?.val(cookie_str)
    cookie_input?.scope().$parent.var.value = cookie_str
  )

  editor = angular.module('HAREditor', [
    'editablelist'
    'upload_ctrl'
    'entry_list'
    'entry_editor'
  ])

  init: -> angular.bootstrap(document.body, ['HAREditor'])
