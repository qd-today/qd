function refresh_modal_load(url) {
    // <a data-load-method="GET" class="modal_load" href="/user/{{ userid }}/manage" title="管理用户">管理用户</a>
    let a = document.createElement("a");
    document.body.appendChild(a);
    a.style = "display: none";
    a.setAttribute('data-load-method', 'GET');
    a.setAttribute('class', 'modal_load');
    a.setAttribute('href', url);
    a.click();
    document.body.removeChild(a);
}
