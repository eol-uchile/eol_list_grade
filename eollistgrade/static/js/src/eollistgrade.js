/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function EolListGradeXBlock(runtime, element, settings) {
    var $ = window.jQuery;
    var $element = $(element);
    var handlerUrlSaveStudentAnswers = runtime.handlerUrl(element, 'savestudentanswers');
    var handlerUrlSaveStudentAnswersAll = runtime.handlerUrl(element, 'savestudentanswersall');
    var handlerUrlImport = runtime.handlerUrl(element, 'import_csv');
    var handlerUrlExport = runtime.handlerUrl(element, 'export_csv');

    function showAnswers(result){
        if (result.result == 'success'){
            var id = result.id
            if (id != "00"){            
                var a =$element.find('.eollistgrade_block table tbody tr[id='+id+']')[0].cells            
                $element.find('#eollistgrade_label')[0].textContent = a[1].textContent + " - Guardado Correctamente"
                $element.find('#eollistgrade_wrong_label')[0].textContent = ""
                $(element).find('#eollistgrade_label').show();
                $(element).find('#eollistgrade_wrong_label').hide();
                if(!result.calificado){
                    $element.find("#calificado_total")[0].textContent = parseInt($element.find("#calificado_total")[0].textContent) + 1
                    if (result.role == 'equipo'){
                        $element.find("#calificado_equipo")[0].textContent = parseInt($element.find("#calificado_equipo")[0].textContent) + 1
                    }
                    if (result.role == 'estudiante'){
                        $element.find("#calificado_alumnos")[0].textContent = parseInt($element.find("#calificado_alumnos")[0].textContent) + 1
                    }
                }
            }
            else{
                $element.find('#eollistgrade_label')[0].textContent = "Guardado Correctamente Todas las Calificaciones"
                $element.find('#eollistgrade_wrong_label')[0].textContent = ""
                $(element).find('#eollistgrade_label').show();
                $(element).find('#eollistgrade_wrong_label').hide();
                $element.find("#calificado_total")[0].textContent = result.n_student
                $element.find("#calificado_equipo")[0].textContent = settings.n_team
                $element.find("#calificado_alumnos")[0].textContent = settings.n_student
            }
        }
        if (result.result == 'error'){
            $element.find('#eollistgrade_label')[0].textContent = ""
            $element.find('#eollistgrade_wrong_label')[0].textContent = "Error de datos o rol de usuario"
            $(element).find('#eollistgrade_label').hide();
            $(element).find('#eollistgrade_wrong_label').show();
        }
        $(element).find('#ui-loading-eollistgrade-load-footer').hide();
    }    

    $(function ($) {
        var  block = $(element).find(".eollistgrade_block");
        block.find('#grade-submissions-button')
            .leanModal()
            
    });
    $(element).find('tr input[type=button]').live('click', function(e) {
        $(element).find('#ui-loading-eollistgrade-load-footer').show();
        $(element).find('#eollistgrade_label').hide();
        $(element).find('#eollistgrade_wrong_label').hide();
        var role = e.target.getAttribute('aria-controls')
        var fila = $(this).closest('tr')
        var colum = fila[0].cells
        var id_student = colum[0].textContent
        var puntaje = colum[3].children[0].value
        var comentario = colum[4].children[0].value
        var pmax = settings.puntajemax
              
        colum[5].children[0].disabled = true
       
        if(puntaje != "" && !(puntaje.includes(".")) && parseInt(puntaje, 10) <= parseInt(pmax, 10) && parseInt(puntaje, 10) >= 0){
            $.ajax({
                type: "POST",
                url: handlerUrlSaveStudentAnswers,
                data: JSON.stringify({"id": id_student, "puntaje": puntaje, "comentario": comentario, "role": role}),
                success: showAnswers                
            });
        }
        else{
            $element.find('#eollistgrade_wrong_label')[0].textContent = "Revise los campos si estan correctos";
            $element.find('#eollistgrade_label')[0].textContent = "";
            $(element).find('#eollistgrade_label').hide();
            $(element).find('#eollistgrade_wrong_label').show();
            $(element).find('#ui-loading-eollistgrade-load-footer').hide();
        }
    });
    $(element).find('input[name=cerrar-eollistgrade]').live('click', function() {
        $("#lean_overlay").click();
    });
    $(element).find('input[name=sendall]').live('click', function() {
        $(element).find('#ui-loading-eollistgrade-load-footer').show();
        $(element).find('#eollistgrade_label').hide();
        $(element).find('#eollistgrade_wrong_label').hide();
        var tabla_alumnos = $element.find('#tabla-alumnos')[0].children;
        var tabla_equipo = $element.find('#tabla-equipo')[0].children;
        var check = true;
        var data =  new Array();
        var pmax = settings.puntajemax
        for(i=0;i<tabla_alumnos.length;i++){
            var id = tabla_alumnos[i].cells[0].textContent
            var punt = tabla_alumnos[i].cells[3].children[0].value
            var com = tabla_alumnos[i].cells[4].children[0].value

            if (punt == "" || punt.includes(".") || parseInt(punt, 10) > parseInt(pmax, 10) || parseInt(punt, 10) < 0){
                check = false
            }
            else{
                var aux =  new Array(id, punt, com);
                data.push(aux)
            }
        }
        for(i=0;i<tabla_equipo.length;i++){
            var id = tabla_equipo[i].cells[0].textContent
            var punt = tabla_equipo[i].cells[3].children[0].value
            var com = tabla_equipo[i].cells[4].children[0].value

            if (punt == "" || punt.includes(".") || parseInt(punt, 10) > parseInt(pmax, 10) || parseInt(punt, 10) < 0){
                check = false
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
                data: JSON.stringify({"data": data}),
                success: showAnswers
            });
        }
        else{
            $element.find('#eollistgrade_wrong_label')[0].textContent = "Revise los campos si estan correctos";
            $element.find('#eollistgrade_label')[0].textContent = "";
            $(element).find('#ui-loading-eollistgrade-load-footer').hide();
            $(element).find('#eollistgrade_label').hide();
            $(element).find('#eollistgrade_wrong_label').show();
        }
    });
    $(element).find('button[id=import-button]').live('click', function() {
        $(element).find('#ui-loading-eollistgrade-load').show();
        $(element).find('#eollistgrade_label')[0].textContent = '';
        $(element).find('#eollistgrade_label')[0].style.display = "none";
        $(element).find('#eollistgrade_wrong_label')[0].textContent = "";
        $(element).find('#eollistgrade_wrong_label')[0].style.display = "none";
        var form_data = new FormData();
        var file_data = $(element).find('#eollistgrade_file').prop('files')[0];
        form_data.append('file', file_data);
        $.ajax({
            url: handlerUrlImport,
            dataType: 'json',
            cache: false,
            contentType: false,
            processData: false,
            data: form_data,
            type: "POST",
            xhrFields: {
                withCredentials: true
                },
            success: function(response) {
                $(element).find('#ui-loading-eollistgrade-load').hide();
                if (response.result == 'success') {
                    $(element).find('#eollistgrade_label')[0].textContent = `${response.total_scored} usuarios fueron calificados.`;
                    $(element).find('#eollistgrade_label')[0].style.display = "block";
                    $(element).find('#eollistgrade_wrong_label')[0].textContent = "";
                    $(element).find('#eollistgrade_wrong_label')[0].style.display = "none";
                    if (response.wrong_data.length > 0){
                        let label = $(element).find('#eollistgrade_wrong_label')[0];
                        label.innerHTML = 'Estos datos estan incorrectos: <br>';
                        response.wrong_data.forEach(function(entry) {
                            label.innerHTML += `${entry.toString()}<br>`
                        });
                        $(element).find('#eollistgrade_wrong_label')[0].style.display = "block";
                    }
                }
                else{
                    $element.find('#eollistgrade_label')[0].textContent = "";
                    $element.find('#eollistgrade_label')[0].style.display = "none";
                    if(response.code_error == 1){
                        $element.find('#eollistgrade_wrong_label')[0].textContent = 'Usuario no tiene permisos para realizar esta acción.';
                    }
                    else if(response.code_error == 2){
                        $element.find('#eollistgrade_wrong_label')[0].textContent = 'No se ha seleccionado un archivo.';
                    }
                    else{
                        $element.find('#eollistgrade_wrong_label')[0].textContent = 'Error al importar el archivo, actualice la página e intente nuevamente, si el problema persiste contáctese a mesa de ayuda.';
                    }
                    $element.find('#eollistgrade_wrong_label')[0].style.display = "block";
                }
            },
            error: function(response){
                $(element).find('#eollistgrade_label')[0].textContent = "";
                $(element).find('#eollistgrade_label')[0].style.display = "none";
                $element.find('#eollistgrade_wrong_label')[0].textContent = 'Error al importar el archivo, actualice la página e intente nuevamente, si el problema persiste contáctese a mesa de ayuda.';
                $(element).find('#eollistgrade_wrong_label')[0].style.display = "block";
            }
        });
    });
    $(element).find('button[id=export-button]').live('click', function() {
        $(element).find('#eollistgrade_label')[0].textContent = `La descarga comenzará en breve.`;
        $(element).find('#eollistgrade_label')[0].style.display = "block";
        $(element).find('#eollistgrade_wrong_label')[0].textContent = "";
        $(element).find('#eollistgrade_wrong_label')[0].style.display = "none";
        location.href = handlerUrlExport;
    });
   $('.decimalx').keyup(function(){
        var val = $(this).val()
        if(isNaN(val) || val.includes(".")){
            val = val.replace(/[^0-9]/g , '')            
        }
        $(this).val(val)  
        var fila = $(this).closest('tr')
        var colum = fila[0].cells
        var pmax = settings.puntajemax

        if (parseInt(val, 10) <= parseInt(pmax, 10) && parseInt(val, 10) >= 0 ){
            colum[5].children[0].disabled = false
        }   
        else{
            colum[5].children[0].disabled = true
        }   
    
    });
    $('.comentario').keyup(function(){
        var fila = $(this).closest('tr')
        var colum = fila[0].cells
        var val = colum[3].children[0].value
        var pmax = settings.puntajemax

        if (parseInt(val, 10) <= parseInt(pmax, 10) && parseInt(val, 10) >= 0 ){
            if (colum[5].children[0].disabled){
                colum[5].children[0].disabled = false
            }                       
        }   
        else{
            colum[5].children[0].disabled = true
        }  
    
    });
    
    $('.outline-button').live('click', function(e) {
        var flecha = e.target.getElementsByClassName('fa-chevron-right')[0]
        var next_block = e.target.getAttribute('aria-controls')
        var block = document.getElementById(next_block)
        if (block){
            if (block.style.display === "block") {
            if (flecha) flecha.className = 'fa fa-chevron-right'
            block.style.display = "none";
            } else {
            if (flecha) flecha.className = 'fa fa-chevron-right fa-rotate-90'
            block.style.display = "block";
            }
        }
    });
}
