# vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-04 19:34:02

define (require, exports, module) ->
  angular.module('contenteditable', [])
    .directive('contenteditable', ['$timeout', ($timeout) -> {
      restrict: 'A'
      require: '?ngModel'
      link: (scope, element, attrs, ngModel) ->
        if !ngModel
          return

        element.bind('input', (e) ->
          scope.$apply ->
            text = element.text()
            ngModel.$setViewValue(text)
            if text == ''
              $timeout ->
                if element.prev().hasClass('contentedit-wrapper')
                  element.prev().click()
                else
                  element[0].blur()
                  element[0].focus()
        )
        element.bind('blur', (e) ->
          text = element.text()
          if ngModel.$viewValue != text
            ngModel.$render()
        )

        oldRender = ngModel.$render
        ngModel.$render = ->
          if !!oldRender
            oldRender()
          if not element.is(':focus')
            element.text(ngModel.$viewValue || '')
    }])
