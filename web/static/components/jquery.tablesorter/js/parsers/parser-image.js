/*! Parser: image - new 7/17/2014 (v2.17.5) */
/* alt attribute parser for jQuery 1.7+ & tablesorter 2.7.11+ */
/* NOTE! Moved to jquery.tablesorter.js (core) in v2.18.0 */
/*jshint jquery:true, unused:false */
;(function($) {
	'use strict';

	$.tablesorter.addParser({
		id: 'image',
		is: function() {
			return false;
		},
		format: function(s, table, cell) {
			return $(cell).find('img').attr(table.config.imgAttr || 'alt') || s;
		},
		parsed : true, // filter widget flag
		type: 'text'
	});

})(jQuery);
