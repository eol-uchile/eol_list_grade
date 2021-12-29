/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function EolListGradeXBlock(runtime, element) {

    $(element).find('.save-button-eollistgrade').bind('click', function(eventObject) {
        eventObject.preventDefault();
        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
        var is_manual = $(element).find('#is_manual').val();
        is_manual = is_manual == '1';
        var data = {
            'display_name': $(element).find('input[name=display_name]').val(),
            'puntajemax': $(element).find('input[name=puntajemax]').val(),
            'is_manual': is_manual,
        };

        if ($.isFunction(runtime.notify)) {
            runtime.notify('save', {state: 'start'});
        }
        $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
            if (response.result == 'success' && $.isFunction(runtime.notify)) {
                runtime.notify('save', {state: 'end'});
            }
            else {
                runtime.notify('error',  {
                    title: 'Error: Falló en Guardar',
                    message: 'Revise los campos si estan correctos.'
                });
            }
        });
    });
    
    $(element).find('.cancel-button-eollistgrade').bind('click', function(eventObject) {
        eventObject.preventDefault();
        runtime.notify('cancel', {});
    });

}