require.config({
    paths: {
			jquery: "../bower_components/jquery/jquery",
			listJs: "../bower_components/list.js/dist/list",
			fuzzySearch: "../bower_components/list.fuzzysearch.js/dist/list.fuzzysearch",
			magnificPopup: "../bower_components/magnific-popup/dist/jquery.magnific-popup"
		},

		shim: {
			jquery: {
				exports: "jquery"
			},
			// responsiveSlides: {
			// 	deps: ['jquery']
			// },
			fuzzySearch: {
				deps: ['listJs'],
			},
			magnificPopup: {
				deps: ['jquery']
			}
		},
	});

require(["app", "domReady", "listJs", "jquery", "fuzzySearch", "magnificPopup"],
				function (app, domReady, List, $, fuzzySearch, magnificPopup) {
	"use strict";

	console.log("Running jQuery %s", $().jquery);

	domReady(function() {

		// Navigation
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
			valueNames: ['size', 'index', 'brand', 'model', 'season', 'price'],
      // listClass: "list",
      // searchClass: "search",
      // sortClass: "sort",
      // indexAsync: "false",
      // page: 200,
			plugins: [ fuzzySearch() ],

		};

		var tyreList = new List('tyre-list', options);

		// ResponsiveSlides
		// $(".rslides").responsiveSlides({
		// 	auto: true,             // Boolean: Animate automatically, true or false
		// 	speed: 500,            // Integer: Speed of the transition, in milliseconds
		// 	timeout: 4000,          // Integer: Time between slide transitions, in milliseconds
		// 	pager: false,           // Boolean: Show pager, true or false
		// 	nav: false,             // Boolean: Show navigation, true or false
		// 	random: false,          // Boolean: Randomize the order of the slides, true or false
		// 	pause: false,           // Boolean: Pause on hover, true or false
		// 	pauseControls: true,    // Boolean: Pause when hovering controls, true or false
		// 	prevText: "Previous",   // String: Text for the "previous" button
		// 	nextText: "Next",       // String: Text for the "next" button
		// 	maxwidth: "",           // Integer: Max-width of the slideshow, in pixels
		// 	navContainer: "",       // Selector: Where controls should be appended to, default is after the 'ul'
		// 	manualControls: "",     // Selector: Declare custom pager navigation
		// 	namespace: "rslides",   // String: Change the default namespace used
		// 	before: function(){},   // Function: Before callback
		// 	after: function(){}     // Function: After callback
		// });

		// Magnific Popup
		$('.popup-link').magnificPopup({
			type: 'image'
			// Some other options to come
		});



	});



});
