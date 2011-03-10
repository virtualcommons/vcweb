/* SlimConsoleDummy.min.js from https://github.com/andyet/ConsoleDummy.js */
/*(function(b){function c(){}for(var d=["error","info","log","warn"],a;a=d.pop();)b[a]=b[a]||c})(window.console=window.console={});*/
if (!window.console) console = {};
console.log = console.log || function(){};
console.warn = console.warn || function(){};
console.error = console.error || function(){};
console.info = console.info || function(){};
