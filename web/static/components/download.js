function AjaxPosSaveFile(response, state, xhr) {
    //result:请求到的结果数据
    //state:请求状态（success）
    //xhr:XMLHttpRequest对象

    // 从Response Headers中获取fileName
    let fileName = xhr.getResponseHeader('Content-Disposition').split(';')[1].split('=')[1].replace(/\"/g, '')
    //获取下载文件的类型
    let type = xhr.getResponseHeader("content-type")
                //结果数据类型处理
    let blob = new Blob([response], { type: type })

    //对于<a>标签，只有 Firefox 和 Chrome（内核）支持 download 属性
    //IE10以上支持blob，但是依然不支持download
    if ('download' in document.createElement('a')) {//支持a标签download的浏览器
        //通过创建a标签实现
        let link = document.createElement("a");
        //文件名
        link.download = fileName;
        link.style.display = "none"
        link.href = URL.createObjectURL(blob);
        document.body.appendChild(link);
        link.click();//执行下载
        URL.revokeObjectURL(link.href);//释放url
        document.body.removeChild(link);//释放标签
    } else {//不支持
        if (window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveOrOpenBlob(blob, fileName)
        }
    }
}
