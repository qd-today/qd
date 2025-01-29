# vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-06 21:16:15

define (require, exports, module) ->
  require '/static/har/contenteditable'
  require '/static/har/editablelist'

  utils = require '/static/components/utils'
  # local_protocol = window.location.protocol
  # local_host = window.location.host
  api_host = "api:/"

  angular.module('entry_editor', [
    'contenteditable'
  ]).controller('EntryCtrl', ($scope, $rootScope, $sce, $http) ->
# init
    $scope.panel = 'request'
    $scope.copy_entry = null

    # on edit event
    $scope.$on('edit-entry', (ev, entry) ->
      console.info(entry)

      $scope.entry = entry
      $scope.entry.success_asserts ?= [{ re: '' + $scope.entry.response.status, from: 'status' }, ]
      $scope.entry.failed_asserts ?= []
      $scope.entry.extract_variables ?= []
      $scope.copy_entry = JSON.parse(utils.storage.get('copy_request'))

      angular.element('#edit-entry').modal('show')
      $scope.alert_hide()
    )

    # on show event
    # angular.element('#edit-entry').on('show.bs.modal', (ev) ->
    #   $rootScope.$broadcast('har-change')
    # )

    # on saved event
    angular.element('#edit-entry').on('hidden.bs.modal', (ev) ->
      if $scope.panel in ['preview-headers', 'preview']
        $scope.$apply ->
          $scope.panel = 'test'

          # update env from extract_variables
          env = utils.list2dict($scope.env)
          for rule in $scope.entry.extract_variables
            if ret = $scope.preview_match?(rule.re, rule.from)
              env[rule.name] = ret
          $scope.env = utils.dict2list(env)

      $scope.$apply ->
        $scope.preview = undefined
      console.debug('har-change')
      $rootScope.$broadcast('har-change')
    )

    # alert message for test panel
    $scope.alert = (message) ->
      angular.element('.panel-test .alert').text(message).show()
    $scope.alert_hide = () ->
      angular.element('.panel-test .alert').hide()

    # sync url with query string
    changing = ''
    $scope.$watch('entry.request.url', () ->
      if changing and changing != 'url'
        changing = ''
        return
      if not $scope.entry?
        return
      if $scope.entry.request.url.substring(0, 2) == "{%"
        return
      try
        queryString = utils.dict2list(utils.querystring_parse_with_variables(utils.url_parse($scope.entry.request.url).query))
      catch error
        queryString = []

      if not changing and not angular.equals(queryString, $scope.entry.request.queryString)
        $scope.entry.request.queryString = queryString
        changing = 'url'
    )
    # sync query string with url
    $scope.$watch('entry.request.queryString', (() ->
      if changing and changing != 'qs'
        changing = ''
        return
      if not $scope.entry?
        return
      if $scope.entry.request.url.substring(0, 2) == "{%"
        return
      url = utils.url_parse($scope.entry.request.url)
      if url? && url.path.indexOf('%7B%7B') > -1
        url.path = utils.path_unparse_with_variables(url.path)
        url.pathname = utils.path_unparse_with_variables(url.pathname)
      url.path = url.path.replace('https:///', 'https://')
      query = utils.list2dict($scope.entry.request.queryString)
      query = utils.querystring_unparse_with_variables(query)
      if query
        url.search = "?#{query}"
      else
        url.search = ""
      url = utils.url_unparse(url)

      if not changing and url != $scope.entry.request.url
        $scope.entry.request.url = url
        changing = 'qs'
    ), true)

    # sync params with text
    $scope.$watch('entry.request.postData.params', (() ->
      if not $scope.entry?.request?.postData?
        return
      if not ($scope.entry.request.postData?.mimeType?.toLowerCase().indexOf("application/x-www-form-urlencoded") == 0)
        return
      obj = utils.list2dict($scope.entry.request.postData.params)
      $scope.entry.request.postData.text = utils.querystring_unparse_with_variables(obj)
    ), true)

    # $scope.$watch('entry.request.postData.text', (function() {
    #   var obj, ref, ref1;
    #   if (((ref = $scope.entry) != null ? (ref1 = ref.request) != null ? ref1.postData : void 0 : void 0) == null) {
    #     return;
    #   }
    #   obj = utils.querystring_parse($scope.entry.request.postData.text);
    #   return $scope.entry.request.postData.params = utils.dict2list(obj);
    # }), true);

    # helper for delete item from array
    $scope.delete = (hashKey, array) ->
      for each, index in array
        if each.$$hashKey == hashKey
          array.splice(index, 1)
          return

    # variables template
    $scope.variables_wrapper = (string, place_holder = '') ->
      string = (string or place_holder).toString()
      string = string.replace(/&/g, '&amp;')
      string = string.replace(/</g, '&lt;')
      string = string.replace(/>/g, '&gt;')
      string = string.replace(/"/g, '&quot;')
      string = string.replace(/'/g, '&#x27;')
      re = /{{\s*([\w]+)[^}]*?\s*}}/g
      $sce.trustAsHtml(string.replace(re, '<span class="label label-primary">$&</span>'))

    $scope.insert_request = (pos, entry) ->
      pos ?= 1
      if (current_pos = $scope.$parent.har.log.entries.indexOf($scope.entry)) == -1
        $scope.alert "can't find position to add request"
        return
      current_pos += pos
      $scope.$parent.har.log.entries.splice(current_pos, 0, entry)
      $rootScope.$broadcast('har-change')
      angular.element('#edit-entry').modal('hide')
      return true

    $scope.add_request = (pos) ->
      $scope.insert_request(pos, {
        checked: false
        pageref: $scope.entry.pageref
        recommend: true
        request: {
          method: 'GET'
          url: ''
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
      })

    $scope.add_for_start = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: 'For 循环开始'
        request: {
          method: 'GET'
          url: '{% for variable in variables %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })


    $scope.add_for_end = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: 'For 循环结束'
        request: {
          method: 'GET'
          url: '{% endfor %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_while_start = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: 'While 循环开始'
        request: {
          method: 'GET'
          url: '{% while int(loop_index0) < While_Limit and Conditional_Expression %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_while_end = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: 'While 循环结束'
        request: {
          method: 'GET'
          url: '{% endwhile %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_if_start = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: '判断条件成立'
        request: {
          method: 'GET'
          url: '{% if Conditional_Expression %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_if_else = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: '判断条件不成立'
        request: {
          method: 'GET'
          url: '{% else %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_if_end = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: '判断块结束'
        request: {
          method: 'GET'
          url: '{% endif %}'
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: []
      })

    $scope.add_timestamp_request = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: '返回对应时间戳和时间'
        request: {
          method: 'POST'
          url: [api_host, '/util/timestamp'].join('')
          postData: {
            text: 'ts=&form=&dt='
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: [
          { re: "200", from: "status" }
        ]
      })

    $scope.add_delay_request = () ->
      $scope.insert_request(1, {
        checked: true
        pageref: $scope.entry.pageref
        recommend: true,
        comment: '延时3秒'
        request: {
          method: 'GET'
          url: [api_host, '/util/delay/3'].join('')
          postData: {
            text: ''
          }
          headers: []
          cookies: []
        }
        response: {}
        success_asserts: [
          {
            re: "200",
            from: "status"
          }
        ]
      })

    $scope.add_unicode_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'Unicode转换',
        request: {
          method: 'POST',
          url: [api_host, '/util/unicode'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "html_unescape=false&content="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"200\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"转换后": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_urldecode_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'URL解码',
        request: {
          method: 'POST',
          url: [api_host, '/util/urldecode'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "unquote_plus=false&encoding=utf-8&content="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"200\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"转换后": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_gb2312_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'GB2312编码',
        request: {
          method: 'POST',
          url: [api_host, '/util/gb2312'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "content="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"200\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"转换后": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_regex_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '正则提取',
        request: {
          method: 'POST',
          url: [api_host, '/util/regex'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "p=&data="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"OK\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"1": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_string_replace_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '字符串替换',
        request: {
          method: 'POST',
          url: [api_host, '/util/string/replace'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "r=json&p=&s=&t="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"OK\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"处理后字符串": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_RSA_Encrypt_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'RSA加密',
        request: {
          method: 'POST',
          url: [api_host, '/util/rsa'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "f=encode&key=&data="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '(.*)',
            from: 'content'
          }
        ]
      })

    $scope.add_RSA_Decrypt_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'RSA解密',
        request: {
          method: 'POST',
          url: [api_host, '/util/rsa'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "f=decode&key=&data="
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '(.*)',
            from: 'content'
          }
        ]
      })

    $scope.add_read_notepad_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '读取记事本',
        variables: {
          qd_email: "",
          qd_pwd: ""
        },
        request: {
          method: 'POST',
          url: [api_host, '/util/toolbox/notepad'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "email={{qd_email|urlencode}}&pwd={{md5(qd_pwd)|urlencode}}&id_notepad=1&f=read"
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '([\s\S]*)',
            from: 'content'
          }
        ]
      })

    $scope.add_append_notepad_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '追加记事本',
        request: {
          method: 'POST',
          url: [api_host, '/util/toolbox/notepad'].join(''),
          headers: [],
          cookies: [],
          postData: {
            text: "email={{qd_email|urlencode}}&pwd={{md5(qd_pwd)|urlencode}}&id_notepad=1&f=append&data={{notebook_content|urlencode}}"
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '([\s\S]*)',
            from: 'content'
          }
        ]
      })

    $scope.add_dddd_OCR_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: 'OCR识别',
        request: {
          method: 'POST',
          url: [api_host, '/util/dddd/ocr'].join(''),
          headers: [{
              "name": "Content-Type",
              "value": "application/json",
              "checked": true
            }],
          cookies: [],
          postData: {
            text: "{\"img\":\"\",\"imgurl\":\"\",\"old\":\"False\",\"extra_onnx_name\":\"\"}"
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"OK\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '"Result": "(.*)"',
            from: 'content'
          }
        ]
      })

    $scope.add_dddd_DET_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '目标检测',
        request: {
          method: 'POST',
          url: [api_host, '/util/dddd/det'].join(''),
          headers: [{
              "name": "Content-Type",
              "value": "application/json",
              "checked": true
            }],
          cookies: [],
          postData: {
            text: "{\"img\":\"\",\"imgurl\":\"\"}"
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"OK\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '(\\d+, \\d+, \\d+, \\d+)',
            from: 'content'
          },
          {
            name: '',
            re: '/(\\d+, \\d+, \\d+, \\d+)/g',
            from: 'content'
          }
        ]
      })

    $scope.add_dddd_SLIDE_request = () ->
      $scope.insert_request(1, {
        checked: true,
        pageref: $scope.entry.pageref,
        recommend: true,
        comment: '滑块识别',
        request: {
          method: 'POST',
          url: [api_host, '/util/dddd/slide'].join(''),
          headers: [{
              "name": "Content-Type",
              "value": "application/json",
              "checked": true
            }],
          cookies: [],
          postData: {
            text: "{\"imgtarget\":\"\",\"imgbg\":\"\",\"comparison\":\"False\",\"simple_target\":\"False\"}"
          }
        },
        response: {},
        success_asserts: [
          {
            re: "200",
            from: "status"
          },
          {
            re: "\"状态\": \"OK\"",
            from: "content"
          }
        ],
        extract_variables: [
          {
            name: '',
            re: '(\\d+, \\d+)',
            from: 'content'
          },
          {
            name: '',
            re: '/(\\d+, \\d+)/g',
            from: 'content'
          }
        ]
      })

    $scope.copy_request = () ->
      if not $scope.entry
        $scope.alert "can't find position to paste request"
        return
      $scope.copy_entry = angular.copy($scope.entry)
      utils.storage.set('copy_request', angular.toJson($scope.copy_entry))

    $scope.paste_request = (pos) ->
      $scope.copy_entry.comment ?= ''
      $scope.copy_entry.comment = 'Copy_' + $scope.copy_entry.comment
      $scope.copy_entry.pageref = $scope.entry.pageref
      $scope.insert_request(pos, $scope.copy_entry)

    $scope.del_request = (pos) ->
        if pos == null
          pos = 1
        if (current_pos = $scope.$parent.har.log.entries.indexOf($scope.entry)) == -1
          $scope.alert("can't find position to add request")
          return
        current_pos += pos
        $scope.$parent.har.log.entries.splice(current_pos, 1)
        $rootScope.$broadcast('har-change')
        return angular.element('#edit-entry').modal('hide')

    # fetch test
    $scope.do_test = () ->
      NProgress.start()
      angular.element('.do-test').button('loading')
      NProgress.inc()
      $http.post('/har/test', {
        request: {
          method: $scope.entry.request.method
          url: $scope.entry.request.url
          headers: ({
            name: h.name,
            value: h.value
          } for h in $scope.entry.request.headers when h.checked)
          cookies: ({
            name: c.name,
            value: c.value
          } for c in $scope.entry.request.cookies when c.checked)
          data: $scope.entry.request.postData?.text
          mimeType: $scope.entry.request.postData?.mimeType
        }
        rule: {
          success_asserts: $scope.entry.success_asserts
          failed_asserts: $scope.entry.failed_asserts
          extract_variables: $scope.entry.extract_variables
        }
        env: {
          variables: utils.list2dict($scope.env)
          session: $scope.session
        }
      }).then((res) ->
        NProgress.inc()
        data = res.data
        status = res.status
        headers = res.headers
        config = res.config
        angular.element('.do-test').button('reset')
        if (status != 200)
          $scope.alert(data)
          return

        $scope.preview = data.har
        $scope.preview.success = data.success
        $scope.env = utils.dict2list(data.env.variables)
        $scope.session = data.env.session
        $scope.panel = 'preview'

        if data.har.response?.content?.text?
          setTimeout((() ->
            angular.element('.panel-preview iframe').attr("src",
              "data:#{data.har.response.content.mimeType};\
              base64,#{data.har.response.content.text}")), 0)
        NProgress.done()
      , (res) ->
        data = res.data
        status = res.status
        headers = res.headers
        config = res.config
        angular.element('.do-test').button('reset')
        console.error('Error_Message', res)
        $scope.alert(data || res.statusText || 'net::ERR_CONNECTION_REFUSED' )
        NProgress.done()
      )

      NProgress.inc()
      $scope.preview_match = (re, from) ->
        data = null
        if not from
          return null
        else if from == 'content'
          if typeof($scope.preview) == 'undefined'
            return false
          content = $scope.preview.response?.content
          if not content? or not content.text?
            return null
          if not content.decoded
            content.decoded = atob(content.text)
          data = content.decoded
        else if from == 'status' & $scope.preview != undefined
          data = '' + $scope.preview.response.status
        else if from.indexOf('header-') == 0
          from = from[7..]
          for header in $scope.preview.response.headers
            if header.name.toLowerCase() == from
              data = header.value
        else if from == 'header'
          data = (h.name + ': ' + h.value for h in $scope.preview.response.headers).join("\n")

        if not data
          return null

        try
          if match = re.match(/^\/(.*?)\/([gimsu]*)$/)
            if match[1]
              re = new RegExp(match[1], match[2])
            else
              throw new Error(match[0] +' is not allowed!')
          else
            re = new RegExp(re)
        catch error
          console.error(error.message)
          return error.message

        if re.global
          try
            result = []
            tmp = re.lastIndex
            while m = re.exec(data)
              result.push(if m[1] then m[1] else m[0])
              if m[0] == ''
                re.lastIndex++
                # throw new Error('the RegExp "' + re.toString() +'" has caused a loop error! Try using stringObject.match(regexp) method on this stringobject...' )
          catch error
            console.error(error.message)
            result = data.match(re)
          console.log('The original result is ', result )
          console.log('The result of toString() is ' + result.toString() )
          return result
        else
          if m = data.match(re)
            return if m[1] then m[1] else m[0]
            # return m[1]
          return null
      NProgress.inc()

## eof
  )
