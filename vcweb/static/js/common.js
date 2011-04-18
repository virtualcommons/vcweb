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

