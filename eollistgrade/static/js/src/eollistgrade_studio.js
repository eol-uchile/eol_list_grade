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

        var data = {
            'display_name': $(element).find('input[name=display_name]').val()
        };
        //console.log(data)
        if ($.isFunction(runtime.notify)) {
            runtime.notify('save', {state: 'start'});
        }
        $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
            if ($.isFunction(runtime.notify)) {
                runtime.notify('save', {state: 'end'});
            }
        });
    });
    
    $(element).find('.cancel-button-eollistgrade').bind('click', function(eventObject) {
        eventObject.preventDefault();
        runtime.notify('cancel', {});
    });

}