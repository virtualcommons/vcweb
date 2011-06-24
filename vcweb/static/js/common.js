if (!window.console) console = {};
console.log = console.log || function(){};
console.warn = console.warn || function(){};
console.error = console.error || function(){};
console.info = console.info || function(){};
function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}
function addChatMessage(elementId, json, title, qtipOptions) {
    if (! title) {
        title = json.date_created;
    }
    if (! qtipOptions) {
        qtipOptions = {position: { corner: {target: 'topMiddle', tooltip: 'bottomMiddle'}}, style: { name: 'green', tip: 'bottomMiddle'} };
    }
    $('#' + elementId).append(
        $("<div class='ui-state-highlight' style='line-height: 1.5em;'/>")
        .append(
            $("<a class='dark-yellow-highlight' />")
            .attr("name", json.pk)
            .attr("title", title)
            .text(json.date_created)
            .qtip(qtipOptions)
        )
        .append(" | ")
        .append(json.message));
    scrollToBottom(document.getElementById(elementId));
}

$(document).ajaxSend(function(event, xhr, settings) {
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", $.cookies.get('csrftoken'));
    }
});
