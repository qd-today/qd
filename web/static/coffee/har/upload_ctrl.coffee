# vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-06 21:12:48

define (require, exports, module) ->
  analysis = require '/static/har/analysis'
  utils = require '/static/components/utils'

  remoteload = () ->
    for each in [/\/har\/edit\/(\d+)/, /\/push\/\d+\/view/, /\/tpl\/\d+\/edit/]
      if location.pathname.match(each)
        return true
    return false

  angular.module('upload_ctrl', []).
    controller('UploadCtrl', ($scope, $rootScope, $http) ->
      element = angular.element('#upload-har')

      element.modal('show').on('hide.bs.modal', -> $scope.is_loaded?)

      element.find('input[type=file]').on('change', (ev) ->
        $scope.file = this.files[0]
      )

      $scope.local_har = utils.storage.get('har_filename') if utils.storage.get('har_har')?

      $scope.alert = (message) ->
        element.find('.alert-danger').text(message).show()

      $scope.loaded = (loaded) ->
        $scope.is_loaded = true
        $rootScope.$emit('har-loaded', loaded)
        angular.element('#upload-har').modal('hide')
        return true

      $scope.load_remote = (url) ->
        element.find('button').button('loading')
        $http.post(url)
        .then((res) ->
          data = res.data
          status = res.status
          headers = res.headers
          config = res.config
          element.find('button').button('reset')
          $scope.loaded(data)
        , (res) ->
          data = res.data
          status = res.status
          headers = res.headers
          config = res.config
          $scope.alert(data)
          element.find('button').button('reset')
        )

      $scope.load_file = (data) ->
        console.log data
        name = ""
        if HARPATH != ""
          name = HARNAME
        else if not $scope.file? && $scope.curl?.length > 0
          name = "curl2har"
        else
          name = $scope.file.name
        if data.log
          loaded = {
            filename: name
            har: analysis.analyze(data, {
                  username: $scope.username
                  password: $scope.password
                })
            upload: true
          }
        else
          loaded = {
            filename: name
            har: utils.tpl2har data
            upload: true
          }

        loaded.env = {}
        for each in analysis.find_variables loaded.har
          loaded.env[each] = ""
        console.log analysis.find_variables loaded.har
        $scope.loaded(loaded)

      $scope.load_local_har = () ->
        loaded = {
          filename: utils.storage.get('har_filename')
          har: utils.storage.get('har_har')
          env: utils.storage.get('har_env')
          upload: true
        }
        $scope.loaded(loaded)

      $scope.delete_local = () ->
        utils.storage.del('har_har')
        utils.storage.del('har_env')
        utils.storage.del('har_filename')

        $scope.local_har = undefined
        if not $scope.local_har and remoteload()
          $scope.load_remote(location.href)

      $scope.add_local = () ->
        if not $scope.file? && $scope.curl?.length? > 0
          element.find('button').button('loading')
          old_har = {
                      filename: utils.storage.get('har_filename'),
                      har: utils.storage.get('har_har'),
                      env: utils.storage.get('har_env'),
                      upload: true
                    }

          # if !old_har.har && typeof(old_har.har)!="undefined" && old_har.har != 0
          # 优先读取本地保存的，如果没有则读取全局的
          old_har = window.global_har if !old_har.har && typeof(old_har.har) != "undefined" && old_har.har != 0

          try
            har_file_upload = utils.curl2har($scope.curl)
          catch e
            console.error e
            $scope.alert('错误的 Curl 命令')
            return element.find('button').button('reset')

          filename = ""
          if HARPATH != ""
            filename = HARNAME
          else if not $scope.file? && $scope.curl?.length? > 0
            filename = "curl2har"
          else if $scope.file?.name?
            # deepcode ignore AttrAccessOnNull: filename is not null
            filename = $scope.file.name
          new_har = {
                        filename: filename,
                        har: analysis.analyze(har_file_upload, {
                          username: $scope.username,
                          password: $scope.password
                        }),
                        upload: true
                      }

          new_har.env = {}
          ref = analysis.find_variables(new_har.har)
          for each in ref
            new_har.env[each] = ""

          if $scope.is_loaded
            target_har = old_har
            for key in new_har
              if new_har.hasOwnProperty(key) == true
                  target_har.env[key] = new_har.env[key]
            for new_har_log_entry in new_har.har.log.entries
              target_har.har.log.entries.push(new_har_log_entry)
          else
            target_har = new_har
          $scope.uploaded = true
          $scope.loaded(target_har)
          return element.find('button').button('reset')
        if not $scope.file?
          $scope.alert('还没选择文件啊，亲')
          return false
        if $scope.file.size > 50 * 1024 * 1024
          $scope.alert('文件大小超过50M')
          return false
        element.find('button').button('loading')
        reader = new FileReader()
        reader.onload = (ev) ->
          return $scope.$apply(() ->
            old_har = {
                        filename: utils.storage.get('har_filename'),
                        har: utils.storage.get('har_har'),
                        env: utils.storage.get('har_env'),
                        upload: true
                      }

            # if !old_har.har && typeof(old_har.har)!="undefined" && old_har.har != 0
            # 优先读取本地保存的，如果没有则读取全局的
            old_har = window.global_har if !old_har.har && typeof(old_har.har) != "undefined" && old_har.har != 0

            har_file_upload = angular.fromJson(ev.target.result)
            new_har = {}
            if har_file_upload.log
              new_har = {
                          filename: $scope.file.name,
                          har: analysis.analyze(har_file_upload, {
                            username: $scope.username,
                            password: $scope.password
                          }),
                          upload: true
                        }
            else
              new_har = {
                          filename: $scope.file.name,
                          har: utils.tpl2har(har_file_upload),
                          upload: true
                        }

            new_har.env = {}
            ref = analysis.find_variables(new_har.har)
            for each in ref
              new_har.env[each] = ""

            if $scope.is_loaded
              target_har = old_har
              for key in new_har
                if new_har.hasOwnProperty(key) == true
                    target_har.env[key] = new_har.env[key]
              for new_har_log_entry in new_har.har.log.entries
                target_har.har.log.entries.push(new_har_log_entry)
            else
              target_har = new_har

            $scope.uploaded = true
            $scope.loaded(target_har)
            return element.find('button').button('reset')
          )
        return reader.readAsText($scope.file)

      if HARDATA != ""
        element.find('button').button('loading')
        reader = new FileReader()
        data = Base64.decode(HARDATA)   # 解码
        $scope.load_file(angular.fromJson(data))
        $scope.local_har = utils.storage.get('har_filename') if utils.storage.get('har_har')?
        element.find('button').button('reset')
        return true
      else
        if not $scope.local_har and remoteload()
          $scope.load_remote(location.href)
        $scope.upload = ->
          if not $scope.file? && $scope.curl?.length? > 0
            element.find('button').button('loading')
            try
              $scope.load_file(utils.curl2har($scope.curl))
            catch error
              console.error error
              $scope.alert('错误的 Curl 命令')
            return element.find('button').button('reset')

          if not $scope.file?
            $scope.alert '还没选择文件啊，亲'
            return false

          if $scope.file.size > 50 * 1024 * 1024
            $scope.alert '文件大小超过50M'
            return false

          element.find('button').button('loading')
          reader = new FileReader()
          reader.onload = (ev) ->
            $scope.$apply ->
              $scope.uploaded = true
              try
                $scope.load_file(angular.fromJson(ev.target.result))
              catch error
                console.error(error)
                $scope.alert('错误的 HAR 文件')

              element.find('button').button('reset')
          reader.readAsText $scope.file
    )
