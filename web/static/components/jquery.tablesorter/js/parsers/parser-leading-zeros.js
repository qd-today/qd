/*! Parser: leading zeros - updated 4/2/2017 (v2.28.6) */
/* jshint jquery:true, unused:false */
;( function( $ ) {
	'use strict';

	var ts = $.tablesorter,
		// modify this value to increase precision as needed
		precision = 1e-10;

	ts.addParser({
		id: 'leadingZeros',
		is: function() {
			return false;
		},
		format: function( s, table ) {
			var val = ( s || '' ).replace( ts.regex.nondigit, '' ),
				number = ts.formatFloat( val, table ),
				str = number.toString();
			if (
				!isNaN( number ) &&
				// eslint-disable-next-line eqeqeq
				number == val && // jshint ignore:line
				val.length !== str.length
			) {
				// subtract a decimal equivalent of the string length
				// so "0001" sorts before "01"
				number -= precision * ( s.length - str.length );
			}
			return number;
		},
		type: 'number'
	});

})( jQuery );
