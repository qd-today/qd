/**
 * @description  draggable polyfill
 * @author       XboxYan
 * @email        yanwenbin1991@live.com
 * @github       https://github.com/XboxYan/draggable-polyfill
 * @license      MIT
 */

/**
 * draggable polyfill
 */
(function () {
    if ("setDragImage" in window.DataTransfer.prototype && document.body.animate) {
        var cloneObj = null;
        var offsetX = 0;
        var offsetY = 0;
        var startX = 0;
        var startY = 0;
        var dragbox = null;
        var axis,_axis;
        var previewImage = new Image();
        previewImage.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' %3E%3Cpath /%3E%3C/svg%3E";
        var styles = document.createElement("style");
        styles.type = "text/css";
        styles.textContent = '[dragging]{position:static!important;box-sizing:border-box!important;margin:0!important;}\
        .drag-obj{position:fixed;left:0;top:0;z-index:999;pointer-events:none;}'
        document.querySelector('head').appendChild(styles);
        HTMLElement.prototype.initDraggable = function () {
            this.init = true;
            this.addEventListener('dragstart', function (ev) {
                dragbox = this;
                dragbox.dragData = {};
                axis = dragbox.getAttribute('axis');
                _axis = axis;
                ev.dataTransfer.setData('text','');
                ev.dataTransfer.setDragImage(previewImage, 0, 0);
                var rect = this.getBoundingClientRect();
                var left = rect.left;
                var top = rect.top;
                startX = ev.clientX;
                startY = ev.clientY;
                offsetX = startX - left;
                offsetY = startY - top;
                this.style.transition = 'none';
                cloneObj = document.createElement('DIV');
                var fakeObj = this.cloneNode(true);
                fakeObj.style.width = this.offsetWidth+'px';
                fakeObj.style.height = this.offsetHeight+'px';
                fakeObj.style.transform = 'translate3d(0,0,0)';
                fakeObj.setAttribute('dragging', '');
                cloneObj.appendChild(fakeObj);
                cloneObj.className = 'drag-obj';
                cloneObj.style = 'transform:translate3d( ' + left + 'px ,' + top + 'px,0);';
                document.body.appendChild(cloneObj);
            })
            this.addEventListener('dragend', function (ev) {
                if(cloneObj){
                    var rect = this.getBoundingClientRect();
                    var left = rect.left;
                    var top = rect.top;
                    var reset = cloneObj.animate(
                        [
                            { transform: cloneObj.style.transform},
                            { transform: 'translate3d('+left+'px,'+top+'px,0)' }
                        ],
                        {
                            duration: 150,
                            easing:"ease-in-out",
                        }
                    )
                    reset.onfinish = function(){
                        document.body.removeChild(cloneObj);
                        cloneObj = null;
                        dragbox.dragData = null;
                        dragbox.style.visibility = 'visible';
                    }
                }
            })
        };

        HTMLElement.prototype.initDrop = function () {
            this.init = true;
            let elementNode = null;
            this.addEventListener('dragover', function(ev) {
                ev.preventDefault();
            })
            this.addEventListener('drop', function(ev) {
                ev.preventDefault();
                ev.stopPropagation();
                this.removeAttribute('over');
            })
            this.addEventListener('dragleave', function(ev) {
                ev.stopPropagation();
                if(elementNode===ev.target){
                    this.removeAttribute('over');
                }
            })
            this.addEventListener('dragenter', function(ev) {
                ev.stopPropagation();
                elementNode = ev.target;
                this.setAttribute('over','');
            })
        }

        document.addEventListener('dragover', function (ev) {
            if (cloneObj) {
                dragbox.style.visibility = 'hidden';
                var left = ~~(ev.clientX - offsetX);
                var top = ~~(ev.clientY - offsetY);
                if(ev.shiftKey || axis ){
                    if(_axis==='X'){
                        top = ~~(startY - offsetY);
                    }else if(_axis==='Y'){
                        left = ~~(startX - offsetX);
                    }else{
                        _axis = ~~Math.abs(ev.clientX-startX)>~~Math.abs(ev.clientY-startY) && 'X' || ~~Math.abs(ev.clientX-startX)<~~Math.abs(ev.clientY-startY) && 'Y' || '';
                    }
                }else{
                    _axis = '';
                }
                startX = left + offsetX;
                startY = top + offsetY;
                cloneObj.style.transform = 'translate3d( ' + left + 'px ,' + top + 'px,0)';
                dragbox.dragData.left = left;
                dragbox.dragData.top = top;
            }
        })

        var observer = new MutationObserver(function (mutationsList) {
            mutationsList.forEach(function (mutation) {
                var target = mutation.target;
                switch (mutation.type) {
                    case 'childList':
                        target.querySelectorAll(':scope [draggable=true],img:not([draggable=false])').forEach(function(el){
                            if(!el.init){
                                el.initDraggable();
                            }
                        });
                        target.querySelectorAll(':scope [allowdrop]').forEach(function(el){
                            if(!el.init){
                                el.initDrop();
                            }
                        });
                        break;
                    default:
                        break;
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
        
        //inject
        document.querySelectorAll(':scope [draggable=true],img:not([draggable=false])').forEach(function(el){
            if(!el.init){
                el.initDraggable();
            }
        });
    }
})();
