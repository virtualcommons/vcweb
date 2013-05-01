/* Use this script if you need to support IE 7 and IE 6. */

window.onload = function() {
	function addIcon(el, entity) {
		var html = el.innerHTML;
		el.innerHTML = '<span style="font-family: \'lighterfootprints\'">' + entity + '</span>' + html;
	}
	var icons = {
			'icon-gauge' : '&#xe000;',
			'icon-question' : '&#xe001;',
			'icon-comment' : '&#xe002;',
			'icon-star' : '&#xe003;',
			'icon-flag' : '&#xe004;',
			'icon-cog' : '&#xf013;',
			'icon-leaf' : '&#xe005;',
			'icon-heart' : '&#xe006;',
			'icon-warning' : '&#xe007;',
			'icon-user' : '&#xe008;',
			'icon-lock' : '&#xe009;',
			'icon-clock' : '&#xe00a;',
			'icon-trophy' : '&#xe00b;',
			'icon-info' : '&#xe00c;',
			'icon-repeat' : '&#xf01e;',
			'icon-checkmark' : '&#xe00d;',
			'icon-cross' : '&#xe00e;'
		},
		els = document.getElementsByTagName('*'),
		i, attr, html, c, el;
	for (i = 0; i < els.length; i += 1) {
		el = els[i];
		attr = el.getAttribute('data-icon');
		if (attr) {
			addIcon(el, attr);
		}
		c = el.className;
		c = c.match(/icon-[^\s'"]+/);
		if (c && icons[c[0]]) {
			addIcon(el, icons[c[0]]);
		}
	}
};