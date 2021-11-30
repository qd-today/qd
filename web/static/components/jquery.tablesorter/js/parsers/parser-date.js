/*! Parser: dates - updated 5/24/2017 (v2.28.11) */
/* Extract dates using popular natural language date parsers */
/*jshint jquery:true */
/*global Sugar*/
;(function($) {
	'use strict';

	/*! Sugar (https://sugarjs.com/docs/#/DateParsing) */
	/* demo: http://jsfiddle.net/Mottie/7z0ss5xn/ */
	$.tablesorter.addParser({
		id: 'sugar',
		is: function() {
			return false;
		},
		format: function(s) {
			// Add support for sugar v2.0+
			var create = Date.create || Sugar.Date.create,
				date = create ? create(s) : s ? new Date(s) : s;
			return date instanceof Date && isFinite(date) ? date.getTime() : s;
		},
		type: 'numeric'
	});

	/*! Datejs (http://www.datejs.com/) */
	/* demo: http://jsfiddle.net/Mottie/zge0L2u6/ */
	$.tablesorter.addParser({
		id: 'datejs',
		is: function() {
			return false;
		},
		format: function(s) {
			var date = Date.parse ? Date.parse(s) : s ? new Date(s) : s;
			return date instanceof Date && isFinite(date) ? date.getTime() : s;
		},
		type: 'numeric'
	});

})(jQuery);
