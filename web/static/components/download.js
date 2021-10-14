function AjaxPosSaveFile(response, xhr) {
    let a = document.createElement("a");
    document.body.appendChild(a);
    a.style = "display: none";
    let data = response;
    let blob = new Blob([data], {type: "octet-stream; charset=utf-8"});  // 二进制大对象
    let url = window.URL.createObjectURL(blob);  // 创建URL对象
    let filename = decodeURIComponent(xhr.getResponseHeader("Content-Disposition").split("filename=")[1].split(";")[0]);  // 文件名
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);  // 释放URL对象
    document.body.removeChild(a);
}
