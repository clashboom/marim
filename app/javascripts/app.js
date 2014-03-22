;(function ($, window, undefined) {
  'use strict';

  var $doc = $(document),
      Modernizr = window.Modernizr;

  $(document).ready(function() {
    $.fn.foundationAlerts           ? $doc.foundationAlerts() : null;
    $.fn.foundationButtons          ? $doc.foundationButtons() : null;
    $.fn.foundationAccordion        ? $doc.foundationAccordion() : null;
    $.fn.foundationNavigation       ? $doc.foundationNavigation() : null;
    $.fn.foundationTopBar           ? $doc.foundationTopBar() : null;
    $.fn.foundationCustomForms      ? $doc.foundationCustomForms() : null;
    $.fn.foundationMediaQueryViewer ? $doc.foundationMediaQueryViewer() : null;
    $.fn.foundationTabs             ? $doc.foundationTabs({callback : $.foundation.customForms.appendCustomMarkup}) : null;
    $.fn.foundationTooltips         ? $doc.foundationTooltips() : null;
    $.fn.foundationMagellan         ? $doc.foundationMagellan() : null;
    $.fn.foundationClearing         ? $doc.foundationClearing() : null;

    $.fn.placeholder                ? $('input, textarea').placeholder() : null;
  });

  // UNCOMMENT THE LINE YOU WANT BELOW IF YOU WANT IE8 SUPPORT AND ARE USING .block-grids
  // $('.block-grid.two-up>li:nth-child(2n+1)').css({clear: 'both'});
  // $('.block-grid.three-up>li:nth-child(3n+1)').css({clear: 'both'});
  // $('.block-grid.four-up>li:nth-child(4n+1)').css({clear: 'both'});
  // $('.block-grid.five-up>li:nth-child(5n+1)').css({clear: 'both'});

  // Hide address bar on mobile devices (except if #hash present, so we don't mess up deep linking).
  if (Modernizr.touch && !window.location.hash) {
    $(window).load(function () {
      setTimeout(function () {
        window.scrollTo(0, 1);
      }, 0);
    });
  }
  
  // jQuery SMOOTH SCROLL TO DIV
  $(function(){

	  $('a[href*=#]').click(function() {
		  if (location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'') 
			  && location.hostname == this.hostname) {
			  var $target = $(this.hash);
			  var parentHeight = $(this).parent().height();
			  $target = $target.length && $target || $('[name=' + this.hash.slice(1) +']');
			  if ($target.length) {
				  var targetOffset = $target.offset().top;
				  $('html,body').animate({scrollTop: targetOffset-parentHeight}, 800); // change number for scroll speed, higher = slower
				  return false;
			  }
		  }
	  });
  });

  // Google maps API

  var myLatlng = new google.maps.LatLng(56.9147,23.9805);
  var mapOptions = {
      zoom: 13,
      center: myLatlng,
      mapTypeId: google.maps.MapTypeId.ROADMAP,
  };
  var map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

  // var image = '../images/maris.jpg';

  var marker = new google.maps.Marker({
      position: myLatlng,
      map: map,
      // icon: image
      title: 'BroPro SIA'

  });

  var lineCoordinates = [
          new google.maps.LatLng(56.917814,23.986609),
          new google.maps.LatLng(56.914949,23.981534)
              ];

  var lineSymbol = {
      path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
  };

  var line = new google.maps.Polyline({
      path: lineCoordinates,
      icons: [{
          icon: lineSymbol,
      offset: '100%'
      }],
      map: map
  });


  // Dynamic top-bar
  var smallScreen = false;
  var navbar = document.getElementById("navbar");
  if ($(window).width() < 940) {
	  navbar.className="fixednavwrap fixed contain-to-grid";
	  smallScreen = true;
  } else {
	  navbar.className="topnavwrap row";
	  $('body').css('padding-top',0)
  }

  window.onscroll = function(){
	  var navbar = document.getElementById("navbar");
	  var classes = navbar.className.split(/\s+/);
      if (getScrollTop() > 90 && !smallScreen) {
          navbar.className="fixednavwrap fixed contain-to-grid";
		  // $('.top-icons').hide();
      } else if (!smallScreen) {
          navbar.className="topnavwrap row";
          $('body').css('padding-top',0)
      }
  }

  function getScrollTop() {
      if (window.onscroll) {
          // Most browsers
          return window.pageYOffset;
      }

      var d = document.documentElement;
      if (d.clientHeight) {
          // IE in standards mode
          return d.scrollTop;
      }

      // IE in quirks mode
      return document.body.scrollTop;
  }

  


})(jQuery, this);
