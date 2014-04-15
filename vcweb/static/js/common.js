if (!window.console) console = {};
console.debug = console.debug || function() {};
console.log = console.log || function(){};
console.warn = console.warn || function(){};
console.error = console.error || function(){};
console.info = console.info || function(){};
if (!window.localStorage) {
  Object.defineProperty(window, "localStorage", new (function () {
    var aKeys = [], oStorage = {};
    Object.defineProperty(oStorage, "getItem", {
      value: function (sKey) { return sKey ? this[sKey] : null; },
      writable: false,
      configurable: false,
      enumerable: false
    });
    Object.defineProperty(oStorage, "key", {
      value: function (nKeyId) { return aKeys[nKeyId]; },
      writable: false,
      configurable: false,
      enumerable: false
    });
    Object.defineProperty(oStorage, "setItem", {
      value: function (sKey, sValue) {
        if(!sKey) { return; }
        document.cookie = escape(sKey) + "=" + escape(sValue) + "; expires=Tue, 19 Jan 2038 03:14:07 GMT; path=/";
      },
      writable: false,
      configurable: false,
      enumerable: false
    });
    Object.defineProperty(oStorage, "length", {
      get: function () { return aKeys.length; },
      configurable: false,
      enumerable: false
    });
    Object.defineProperty(oStorage, "removeItem", {
      value: function (sKey) {
        if(!sKey) { return; }
        document.cookie = escape(sKey) + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      },
      writable: false,
      configurable: false,
      enumerable: false
    });
    this.get = function () {
      var iThisIndx;
      for (var sKey in oStorage) {
        iThisIndx = aKeys.indexOf(sKey);
        if (iThisIndx === -1) { oStorage.setItem(sKey, oStorage[sKey]); }
        else { aKeys.splice(iThisIndx, 1); }
        delete oStorage[sKey];
      }
      for (aKeys; aKeys.length > 0; aKeys.splice(0, 1)) { oStorage.removeItem(aKeys[0]); }
      for (var aCouple, iKey, nIdx = 0, aCouples = document.cookie.split(/\s*;\s*/); nIdx < aCouples.length; nIdx++) {
        aCouple = aCouples[nIdx].split(/\s*=\s*/);
        if (aCouple.length > 1) {
          oStorage[iKey = unescape(aCouple[0])] = unescape(aCouple[1]);
          aKeys.push(iKey);
        }
      }
      return oStorage;
    };
    this.configurable = false;
    this.enumerable = true;
  })());
}
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
