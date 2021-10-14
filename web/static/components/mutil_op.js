function del_confirm() {
  $('#multi_op-result').html('<div class="alert alert-info" role="alert">\
        您正在删除多个任务，是否继续？\
        <a href="javascript:void(0);" onclick="Del_tasks()"> 继续 </a> /\
        <a href="javascript:void(0);" onclick="goto_my()">取消</a> \
      </div>').show();
}

function Null_info() {
    $('#multi_op-result').html('<div class="alert alert-info" role="alert">\
          请选择任务！\
          <a href="javascript:void(0);" onclick="goto_my()"> 返回 </a> \
        </div>').show();
}

function Get_Groups() {
  var str1 = '<div class="alert alert-info" role="alert">\
  您正在设置多个任务的分组，是否继续？\
  <a href="javascript:void(0);" onclick="setTasksGroup()"> 继续 </a> /\
  <a href="javascript:void(0);" onclick="goto_my()">取消</a> \
  </div>\
    <div class="use_redpackets_content" id="oneCheck"><label class="control-label" for="note">选择分组</label>'
  var str2 = '<div class="checkbox"><label><input type="checkbox" name="'
  var str3 = '</label></div>'   
  var str4 = '</div>\
  <div class="form-group">\
    <label class="control-label" for="note">新分组</label>\
    <input type="text" class="form-control" name="NewGroupValue" value="" id="NewGroupValue" placeholder="None">\
  </div>\
  '
  var Indexs = {};
  var es = document.querySelectorAll('tr[class*=taskgroup]');
  var tmp = ""
  es.forEach(function(entry){
  var tmp = entry.getElementsByTagName('td')[0].getElementsByTagName('input')[0]
  if (tmp.checked){
      Indexs[tmp.name] = ''
  }
  });
  if (Object.keys(Indexs).length > 0){
    var groupurl = '/getgroups/'+ Object.keys(Indexs)[0]
    $.get(groupurl, function(result){
        tmp = JSON.parse(result)
        var groupinfo = ""
        Object.keys(tmp).forEach(function(key){
            groupinfo = groupinfo + str2 + key + '">' + key + str3;
        });
        $("#multi_op-result").html(str1 + groupinfo + str4).show();
        OnlyCheckOne()
      });
  }
  else{
      Null_info()
  }
  return false;
}

function goto_my () {
  window.location.replace("/my/")
}

function OnlyCheckOne() {
    var fanxiBox = $("#oneCheck input:checkbox");
    fanxiBox.click(function () {
    if(this.checked || this.checked=='checked'){
        fanxiBox.removeAttr("checked");
        $(this).prop("checked", true);
        }
    });
};   

function Del_tasks () {
  var Indexs = {};
  var es = document.querySelectorAll('tr[class*=taskgroup]');
  es.forEach(function(entry){
    var tmp = entry.getElementsByTagName('td')[0].getElementsByTagName('input')[0]
    if (tmp.checked){
      Indexs[tmp.name] = ''
    }
  });
  var $this = $(this);
  var data = {taskids: JSON.stringify(Indexs), func: "Del"}
  $.ajax('/tasks/{{ userid }}', {
      type: 'POST',
      data: data,
    })
    .done(function(data) {
      goto_my()
    })
    .fail(function(jxhr) {
      $("del_confirm-result").html('<h1 class="alert alert-danger text-center">失败</h1><div class="well"></div>').show().find('div').text(jxhr.responseText);
    })
    .always(function() {
      $this.button('reset');});

  return false;
}

function setTasksGroup() {
    var Indexs = {};
    var es = document.querySelectorAll('tr[class*=taskgroup]');
    var tmp = ""
    var groupValue = ''
    es.forEach(function(entry){
    var tmp = entry.getElementsByTagName('td')[0].getElementsByTagName('input')[0]
    if (tmp.checked){
        Indexs[tmp.name] = ''
    }
    });
    
    tmp = document.querySelectorAll('#NewGroupValue')[0]
    if(tmp.value == ''){
    es = document.querySelectorAll('#oneCheck input[type=checkbox]');
    es.forEach(function (e){
        if (e.checked) {
        groupValue = e.name;
        }
    });
    }
    else {
    groupValue = tmp.value
    }
    var $this = $(this);
    var data = {taskids: JSON.stringify(Indexs), func: "setGroup", groupValue: groupValue}
    $.ajax('/tasks/{{ userid }}', {
        type: 'POST',
        data: data,
    })
    .done(function(data) {
        window.location.replace("/my/")
    })
    .fail(function(jxhr) {
        $('#run-result').html('<h1 class="alert alert-danger text-center">失败</h1><div class="well"></div>').show().find('div').text(jxhr.responseText);
    })
    .always(function() {
        $this.button('reset');});

    return false;
}