/*! Parser: hugeNumbers - updated 3/1/2016 (v2.25.5) *//*
 * See https://github.com/Mottie/tablesorter/issues/1161
 */
/*jshint jquery:true */
;( function( $ ) {
	'use strict';

	$.tablesorter.addParser({
		id: 'hugeNumbers',
		is : function() {
			return false;
		},
		format : function( str ) {
			// add commas every 12 digits; Number.MAX_SAFE_INTEGER is 16 digits long
			// regex modified from: http://stackoverflow.com/a/2901298/145346
			return str.replace(/\B(?=(\d{12})+(?!\d))/g, ',');
		},
		type : 'text'
	});

})( jQuery );
