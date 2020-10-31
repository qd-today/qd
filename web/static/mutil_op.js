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

function groups_click(checkbox) {
    var tmp = checkbox.title
    var tasknodes = document.getElementsByClassName(tmp);
    if (tasknodes.length > 0){
        tmp = tasknodes[0].style.display;
        for (i = 0; i < tasknodes.length; i++) { 
            if (tmp == '' || tmp == 'table-row'){
            $(tasknodes[i]).hide();
            }else{
            $(tasknodes[i]).show();
            }
        }
    } 
}
