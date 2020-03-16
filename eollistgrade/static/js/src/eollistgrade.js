/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function EolListGradeXBlock(runtime, element) {
    var $ = window.jQuery;
    var $element = $(element);
    var handlerUrlSaveStudentAnswers = runtime.handlerUrl(element, 'savestudentanswers');
    var handlerUrlSaveStudentAnswersAll = runtime.handlerUrl(element, 'savestudentanswersall');

    function showAnswers(result){
        var id = result.id
        if (id != "00" && result.result == 'success'){            
            var a =$element.find('.eollistgrade_block table tbody tr[id='+id+']')[0].cells
            a[2].children[0].value = ""
            a[3].children[0].value = ""
            $element.find('.eollistgrade_block label')[0].textContent = a[1].textContent + " - Guardado Correctamente"
        }
        if (id == "00" && result.result == 'success'){
            $element.find('.eollistgrade_block label')[0].textContent = "Guardado Correctamente Todos"
        }
    }

    $(function ($) {
        var  block = $(element).find(".eollistgrade_block");
        block.find('#grade-submissions-button')
            .leanModal()
            
    });

    $('tr input[type=button]').live('click', function () {        
       
        var fila = $(this).closest('tr')
        var colum = fila[0].cells
        var id_student = colum[0].textContent
        var puntaje = colum[2].children[0].value
        var comentario = colum[3].children[0].value
        var pmax = $element.find('.eollistgrade_block input[name=ptjemax]')[0].value
        if (pmax == ""){
            pmax= "100"
        }
        
        colum[4].children[0].disabled = true
        if(puntaje != ""){
            $.ajax({
                type: "POST",
                url: handlerUrlSaveStudentAnswers,
                data: JSON.stringify({"id": id_student, "puntaje": puntaje, "comentario": comentario, "puntajemax": pmax}),
                success: showAnswers
            });
        }
    });

    $('input[name=sendall]').live('click', function () {        
        var tabla = $element.find('#tabla-alumnos')[0].children;
        var pmax = $element.find('.eollistgrade_block input[name=ptjemax]')[0].value;
        var check = true;
        var data =  new Array();
        for(i=0;i<tabla.length;i++){          
            var id = tabla[i].cells[0].textContent            
            var punt = tabla[i].cells[2].children[0].value
            var com = tabla[i].cells[3].children[0].value
            if (parseInt(punt, 10) > parseInt(pmax, 10) || punt == ""){
                check = false
                $element.find('.eollistgrade_block label')[0].textContent = "Revise los campos si estan correctos"                
            }
            else{
                var aux =  new Array(id, punt, com);
                data.push(aux)
            }            
        }       
        if (check){
            $.ajax({
                type: "POST",
                url: handlerUrlSaveStudentAnswersAll,
                data: JSON.stringify({"data": data, "puntajemax": pmax}),
                success: showAnswers
            });
        }
    });

   $('.decimalx').keyup(function(){
        var val = $(this).val()
        if(isNaN(val)){
            val = val.replace(/[^0-9\.]/g , '')
            if(val.split('.').length > 2){ 
                val = val.replace(/\.+$/ , "")
            }
        }
        $(this).val(val)
        var pmax = $element.find('.eollistgrade_block input[name=ptjemax]')[0].value
        if (pmax == ""){
            pmax= "100"
        }
        var fila = $(this).closest('tr')
        var colum = fila[0].cells  
        if (parseInt(val, 10) <= parseInt(pmax, 10) ){
            colum[4].children[0].disabled = false
        }   
        else{
            colum[4].children[0].disabled = true
        }   
    
    });
    $('.comentario').keyup(function(){
        var pmax = $element.find('.eollistgrade_block input[name=ptjemax]')[0].value
        if (pmax == ""){
            pmax= "100"
        }
        var fila = $(this).closest('tr')
        var colum = fila[0].cells
        var val = colum[2].children[0].value
        if (parseInt(val, 10) <= parseInt(pmax, 10) ){
            if (colum[4].children[0].disabled){
                colum[4].children[0].disabled = false
            }                       
        }   
        else{
            colum[4].children[0].disabled = true
        }  
    
    });
    $('.ptjemax').keyup(function(){
        var val = $(this).val()
        if(isNaN(val)){
            val = val.replace(/[^0-9\.]/g , '')
            if(val.split('.').length > 2){ 
                val = val.replace(/\.+$/ , "")
            }
        }
        $(this).val(val)
       
        var trs =$element.find('.eollistgrade_block table tbody tr')
        if(val == ""){
            val=100
        }
        
        for(i=0;i<trs.length;i++){
            var tds = trs[i].cells[2]
            var labelmax = tds.children.max
            labelmax.textContent = val
            var punt = trs[i].cells[2].children[0].value
            if(punt == ""){
                punt=parseInt(val, 10)+1
            }
            var inp = trs[i].cells[4].children[0]
            
            if (parseInt(punt, 10) <= parseInt(val, 10) ){
                inp.disabled = false
            }   
            else{
                inp.disabled = true
            } 
        }
    });
}
