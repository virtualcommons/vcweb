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
var csrftoken = $.cookie('csrftoken');
$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});
