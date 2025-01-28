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

  # $(() ->
  #   if $('body').attr('get-cookie') == 'true'
  #     $('[data-toggle=get-cookie][disabled]').attr('disabled', false)
  #   return
  # )

  # get cookie helper
  cookie_input = null
  $(document).on('click', "[data-toggle=get-cookie]", (ev) ->
    $this = $(this)
    # if $this.attr('disabled')
    #   return
    cookie_input = angular.element($this.parent().find('input'))

    if $('body').attr('get-cookie') != 'true'
      # $this.html('没有插件，详情F12')
      # console.log('如需要插件请访问 https://github.com/qd-today/get-cookies/ 下载并手动安装插件')
      if $this.attr('getmod') == 1
        $this.attr('href', 'https://github.com/qd-today/get-cookies/')
        .attr('target', '_blank').html('安装插件后请刷新')
      else
        $this.attr('getmod', 1)
        .html('再次点击前往安装 Get-Cookies 插件')
      return
  )
  # deepcode ignore InsufficientPostmessageValidation: the event.origin is checked
  window.addEventListener("message", (ev) ->
    if event.origin != window.location.origin
      return
    cookie = ev.data
    cookie_str = ""
    # 排除未带特定key的postMessage
    if !cookie.info
      return
    if cookie.info == 'cookieRaw'
      for key, value of cookie.data
        cookie_str += key + '=' + value + '; '
      if cookie_str == ''
        console.log('没有获得cookie, 您是否已经登录?')
        return
    else if cookie.info == 'get-cookieModReady'
      cookie_str = "get-cookie扩展已就绪"
    cookie_input?.val(cookie_str)
    cookie_input?.scope().$parent.var.value = cookie_str
  )

  editor = angular.module('HAREditor', [
    'editablelist'
    'upload_ctrl'
    'entry_list'
    'entry_editor'
  ])

  { init: ->
    angular.bootstrap(document.body, ['HAREditor'])
  }
