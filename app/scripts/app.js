/*global define */
define([], function () {
	'use strict';

	// Thanks, David Bushell.

	// helper functions

	var trim = function(str) {
		return str.trim ? str.trim() : str.replace(/^\s+|\s+$/g,'');
	};

	var hasClass = function(el, cn) {
		return (' ' + el.className + ' ').indexOf(' ' + cn + ' ') !== -1;
	};

	var addClass = function(el, cn) {
		if (!hasClass(el, cn)) {
			el.className = (el.className === '') ? cn : el.className + ' ' + cn;
		}
	};

	var removeClass = function(el, cn) {
		el.className = trim((' ' + el.className + ' ').replace(' ' + cn + ' ', ' '));
	};

	var hasParent = function(el, id) {
		if (el) {
			do {
				if (el.id === id) {
					return true;
				}
				if (el.nodeType === 9) {
					break;
				}
			}
			while((el = el.parentNode));
		}
		return false;
	};

		// normalize vendor prefixes

	var doc = document.documentElement;

	var transformProp = window.Modernizr.prefixed('transform'),
			transitionProp = window.Modernizr.prefixed('transition'),
			transitionEnd = (function() {
				var props = {
					'WebkitTransition' : 'webkitTransitionEnd',
					'MozTransition'    : 'transitionend',
					'OTransition'      : 'oTransitionEnd otransitionend',
					'msTransition'     : 'MSTransitionEnd',
					'transition'       : 'transitionend'
				};
				return props.hasOwnProperty(transitionProp) ? props[transitionProp] : false;
			})();



	var _init = false, app = { };

	var inner = document.getElementById('inner-wrap');
	var navOpen = false;
	var navClass = 'js-nav';


	app.init = function() {
			if (_init) {
				return;
			}
			_init = true;

			var closeNavEnd = function(e) {
				if (e && e.target === inner) {
					document.removeEventListener(transitionEnd, closeNavEnd, false);
				}
				navOpen = false;
			};

			app.closeNav =function()
			{
				if (navOpen) {
					// close navigation after transition or immediately
					var duration = (transitionEnd && transitionProp) ? parseFloat(window.getComputedStyle(inner, '')[transitionProp + 'Duration']) : 0;
					if (duration > 0) {
						document.addEventListener(transitionEnd, closeNavEnd, false);
					} else {
						closeNavEnd(null);
					}
				}
				removeClass(doc, navClass);
			};

			app.openNav = function()
			{
				if (navOpen) {
					return;
				}
				addClass(doc, navClass);
				navOpen = true;
			};

			app.toggleNav = function(e)
			{
				if (navOpen && hasClass(doc, navClass)) {
					app.closeNav();
				} else {
					app.openNav();
				}
				if (e) {
					e.preventDefault();
				}
			};

			// open nav with main "nav" button
			document.getElementById('nav-open').addEventListener('click', app.toggleNav, false);

			// close nav with main "close" button
			document.getElementById('nav-close').addEventListener('click', app.toggleNav, false);

			// close nav by touching the partial off-screen content
			document.addEventListener('click', function(e)
					{
						if (navOpen && !hasParent(e.target, 'nav')) {
							e.preventDefault();
							app.closeNav();
						}
					},
					true);

			addClass(doc, 'js-ready');

		};

	return app;

});
