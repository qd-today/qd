// vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
// QD AI 智能识别签到 控制器
(function() {
  define(function(require, exports, module) {
    var analysis = require('/static/har/analysis');
    var utils = require('/static/components/utils');
    return angular.module('ai_ctrl', []).controller('AIAnalyzeCtrl', function($scope, $rootScope, $http) {
      $scope.ai_enabled = false;
      $scope.ai_model = '';
      $scope.hint = '';
      $scope.error = '';
      $scope.result = null;
      $scope.result_text = '';

      // 初始查询 AI 状态
      $http.get('/har/ai_status').then(function(res) {
        $scope.ai_enabled = !!(res.data && res.data.enabled);
        $scope.ai_model = (res.data && res.data.model) || '';
      }, function() {
        $scope.ai_enabled = false;
      });

      $scope.ai_open = function() {
        $scope.error = '';
        $scope.result = null;
        $scope.result_text = '';
      };

      // 把当前编辑器中的 har 转回标准 HAR 格式发给后端
      function collect_har() {
        // window.global_har 由 entry_list 维护，结构为 {filename, har: {log:{entries:[]}}, env}
        var src = (window.global_har && window.global_har.har) ? window.global_har.har : null;
        if (!src) return null;
        return src;
      }

      $scope.run = function() {
        var btn = $('#ai-analyze .btn-primary');
        var har = collect_har();
        if (!har) {
          $scope.error = '当前没有 HAR 数据，请先上传或编辑 HAR 后再使用';
          return;
        }
        $scope.error = '';
        $scope.result = null;
        $scope.result_text = '正在调用 AI 分析中，请稍候...';
        btn.button('loading');
        $http.post('/har/ai_analyze', {har: har, hint: $scope.hint || ''}).then(function(res) {
          btn.button('reset');
          if (!res.data || !res.data.ok) {
            $scope.error = (res.data && res.data.error) || 'AI 分析失败';
            $scope.result_text = '';
            return;
          }
          $scope.result = res.data;
          try {
            $scope.result_text = JSON.stringify(res.data.result, null, 2);
          } catch (e) {
            $scope.result_text = String(res.data.result);
          }
        }, function(res) {
          btn.button('reset');
          var msg = '请求失败';
          if (res && res.data && res.data.error) {
            msg = res.data.error;
          } else if (res && res.status) {
            msg = 'HTTP ' + res.status;
          }
          $scope.error = msg;
          $scope.result_text = '';
        });
      };

      // 把 AI 给出的精简 HAR 应用到编辑器
      $scope.apply = function() {
        if (!$scope.result || !$scope.result.har) return;
        var loaded = {
          filename: ($scope.result.result && $scope.result.result.sitename) || 'AI 生成模板',
          har: analysis.analyze($scope.result.har, {}),
          upload: true
        };
        loaded.env = {};
        var vars = analysis.find_variables(loaded.har) || [];
        for (var i = 0; i < vars.length; i++) {
          loaded.env[vars[i]] = '';
        }
        $rootScope.$emit('har-loaded', loaded);
        angular.element('#ai-analyze').modal('hide');
      };
    });
  });
}).call(this);
