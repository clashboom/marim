var app = (function(document, $) {

	'use strict';
	var docElem = document.documentElement,

		_userAgentInit = function() {
			docElem.setAttribute('data-useragent', navigator.userAgent);
		},
		_init = function() {
			$(document).foundation();
			_userAgentInit();
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

  // Calculating shopping cart values
  if ($('#shopping-cart-total').length) {

    $(".remove").click(function(){
      confirm('Tiešām dzēst?');
    });

    var total_sum = 0.0;

    $('.item-count').each(function(){
        var count = parseInt($(this).val());
        var price = parseFloat($(this).parent().prev().children('.item-price').text());
        var sum = (count * price);
        $(this).parent().siblings().last('.item-sum').html(sum.toFixed(2));
        if (!isNaN(sum)) total_sum += sum;
        console.log(total_sum);
    });

    $('#shopping-cart-total').html(total_sum.toFixed(2));


    $(".item-count").data("previously", $('.item-count').val());
    $('.item-count').on('focus', function(){
      $(this).attr('oldValue', $(this).val());
    });

    $('.item-count').change(function(){

        var price = parseFloat($(this).parent().prev().children('.item-price').text());

        var previous_val = parseInt($(this).data("previously"));
        var previous_sum = (price * previous_val);

        var count = parseInt($(this).val());
        var price = parseFloat($(this).parent().prev().children('.item-price').text());
        var sum = (count * price);
        $(this).parent().siblings().last('.item-sum').html(sum.toFixed(2));

        var current_total = parseFloat($('#shopping-cart-total').html());
        var new_total = (current_total - previous_sum + sum).toFixed(2);
        $('#shopping-cart-total').html(new_total);

        $(this).data("previously", $(this).val());

    });
  };

  // Form control
  if ($('#add-tyre-form').length) {
    $('#truck-tyre-properties').hide();
    $('#tread').hide();
    $('#condition').parent().removeClass('small-6').addClass('small-12');

    $('#condition').change(function(){
      if ($(this).val() == 'used') {
        $('#condition').parent().removeClass('small-12').addClass('small-6');
        $("#tread").show();
      } else {
        $("#tread").hide();
        $('#condition').parent().removeClass('small-6').addClass('small-12');
      };
    });

    $("#tyre-kind").change(function(){
      if ($(this).val() == "truck") {
        $('#truck-tyre-properties').show();
      } else {
        $('#truck-tyre-properties').hide();

      };
    });
  };

  // Search bar
  $('#tyre-search-submit').click(function(){
    listObj.fuzzySearch.search($('#tyre-search-input').val());
  });
;

  console.log($().jquery);


})();
