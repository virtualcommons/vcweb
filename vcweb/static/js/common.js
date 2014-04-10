if (!window.console) console = {};
console.debug = console.debug || function() {};
console.log = console.log || function(){};
console.warn = console.warn || function(){};
console.error = console.error || function(){};
console.info = console.info || function(){};
function scrollToTop() {
    // $("html, body").animate({ scrollTop: 0 }, "fast");
    window.scrollTo(0, 0);
}
function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}
function formatCurrency(floatValue) {
    return "$" + floatValue.toFixed(2);
}
var INT_REGEX = /^\d+$/;
function isInt(value) {
    return INT_REGEX.test(value);
}
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
function activateTabFunctor(tabHref, parentId, callback) {
    if (! parentId) {
        parentId = ".nav-tabs";
    }
    return function() {
        $(parentId + ' a[href="' + tabHref + '"]').tab('show');
        if (callback && typeof(callback) === 'function') {
            callback();
        }
    }
}
function preserveLastSelectedTab() {
    // use HTML5 local storage to restore the last selected tab on refresh (or any return visit for that matter)
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        var lastTabId = $(e.target).attr('href')
        localStorage.setItem('lastTabId', lastTabId);
    });
    var lastTabId = localStorage.getItem('lastTabId');
    if (lastTabId) {
        // activate tab by invoking show on its a data-toggle tag
        $("a[data-toggle='tab'][href='" + lastTabId + "']").tab('show');
    }
}
var csrftoken = $.cookie('csrftoken');
$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

$(function() {
    $('a.external').attr('target', '_blank');
});
