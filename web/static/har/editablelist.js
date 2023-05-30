// Generated by CoffeeScript 2.7.0
(function() {
  // vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
  // Author: Binux<i@binux.me>
  //         http://binux.me
  // Created on 2014-08-05 14:47:55
  define(function(require, exports, module) {
    return angular.module('editablelist', []).directive('editablelist', function() {
      return {
        restrict: 'A',
        scope: true,
        templateUrl: '/static/har/editablelist.html',
        link: function($scope, $element, $attr, ctrl, $transclude) {
          $scope.$filter = $scope.$eval($attr.filter);
          return $scope.$watch($attr.editablelist, function(value) {
            return $scope.$list = value;
          });
        }
      };
    });
  });

}).call(this);