function reserve_check() {
      document.querySelectorAll('#droplist>a.list-group-item.entry').forEach(function(el){
        var tmp = el.getElementsByClassName('entry-checked')[0].getElementsByTagName('input')[0]
        tmp.checked = !tmp.checked
    });
    entries = window.global_har.har.log.entries
    for (i = 0; i < entries.length;i++)
    {
      entries[i].checked = !entries[i].checked
    }
}