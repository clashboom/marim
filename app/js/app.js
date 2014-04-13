var app = (function(document, $) {

	'use strict';
	var docElem = document.documentElement,

		_userAgentInit = function() {
			docElem.setAttribute('data-useragent', navigator.userAgent);
		},
		_init = function() {
			$(document).foundation();
			_userAgentInit();
            console.log('Maybe. Maybe not. Maybe go fuck yourself.');
		};

	return {
		init: _init
	};

})(document, jQuery);

(function() {

	'use strict';
	app.init();

  // List.js
  var fuzzyOptions = {
    searchClass: "fuzzy-search",
    location: 0,
    distance: 100,
    threshold: 0.4,
    multiSearch: true
  };

  var options = {
    valueNames: ['brand', 'model', 'size'],
    page: 12,
    paginationClass: "pagination",
    innerWindow: 2,
    plugins: [ListFuzzySearch(), ListPagination({})]
  };

  var listObj = new List('tire-list', options);


console.log('got this far');

})();
