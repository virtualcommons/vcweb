/* SlimConsoleDummy.min.js from https://github.com/andyet/ConsoleDummy.js */
/*(function(b){function c(){}for(var d=["error","info","log","warn"],a;a=d.pop();)b[a]=b[a]||c})(window.console=window.console={});*/
if (!window.console) console = {};
console.log = console.log || function(){};
console.warn = console.warn || function(){};
console.error = console.error || function(){};
console.info = console.info || function(){};
function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}
function addChatMessage(elementId, json, title) {
    if (! title) {
        title = json.date_created;
    }
    $('#' + elementId).append(
        $("<div class='ui-state-highlight' style='line-height: 1.5em;'/>")
        .append($("<a class='dark-yellow-highlight' />").attr("name", json.pk).attr("title", title)
            .text(json.date_created))
        .append(" | ")
        .append(json.message));
    scrollToBottom(document.getElementById(elementId));
}

