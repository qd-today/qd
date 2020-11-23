function checkboxOnclick(checkbox){
    var tasknodes = document.getElementsByClassName(checkbox.name);
    for (i = 0; i < tasknodes.length; i++) { 
        if (checkbox.checked == true){
        $(tasknodes[i]).hide();
        window.localStorage.Groups = "1"
        }else{
        $(tasknodes[i]).show();
        }
    }
    
}
