/*! Parser: date ranges -updated 11/22/2015 (v2.24.6) */
/* Include the 'widget-filter-type-insideRange.js' to filter ranges */
/*jshint jquery:true */
;(function($) {
	'use strict';

	var ts = $.tablesorter,
	getMonthVal,

	regex = {
		mdy        : /(\d{1,2}[-\s]\d{1,2}[-\s]\d{4}(\s+\d{1,2}:\d{2}(:\d{2})?(\s+[AP]M)?)?)/gi,

		dmy        : /(\d{1,2}[-\s]\d{1,2}[-\s]\d{4}(\s+\d{1,2}:\d{2}(:\d{2})?(\s+[AP]M)?)?)/gi,
		dmyreplace : /(\d{1,2})[-\s](\d{1,2})[-\s](\d{4})/,

		ymd        : /(\d{4}[-\s]\d{1,2}[-\s]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?(\s+[AP]M)?)?)/gi,
		ymdreplace : /(\d{4})[-\s](\d{1,2})[-\s](\d{1,2})/,

		// extract out date format (dd MMM yyyy hms) e.g. 13 March 2016 12:55 PM
		overall_dMMMyyyy : /(\d{1,2}\s+\w+\s+\d{4}(\s+\d{1,2}:\d{2}(:\d{2})?(\s\w+)?)?)/g,
		matches_dMMMyyyy : /(\d{1,2})\s+(\w+)\s+(\d{4})/

	};

	/*! date-range MMDDYYYY *//* (2/15/2000 - 5/18/2000) */
	$.tablesorter.addParser({
		id: 'date-range-mdy',
		is: function () {
			return false;
		},
		format: function (text) {
			var date, str, i, len,
				parsed = [];
			str = text.replace( /\s+/g, ' ' ).replace( /[\/\-.,]/g, '-' ).match( regex.mdy );
			len = str && str.length;
			// work on dates, even if there is no range
			if ( len ) {
				for (i = 0; i < len; i++) {
					date = new Date( str[i] );
					parsed.push( date instanceof Date && isFinite(date) ? date.getTime() : str[i] );
				}
				// sort from min to max
				return parsed.sort().join( ' - ' );
			}
			return text;
		},
		type: 'text'
	});

	/*! date-range DDMMYYYY *//* (15/2/2000 - 18/5/2000) */
	$.tablesorter.addParser({
		id: 'date-range-dmy',
		is: function () {
			return false;
		},
		format: function (text) {
			var date, str, i, len,
				parsed = [];
			str = text.replace( /\s+/g, ' ' ).replace( /[\/\-.,]/g, '-' ).match( regex.dmy );
			len = str && str.length;
			if ( len ) {
				for (i = 0; i < len; i++) {
					date = new Date( ( '' + str[i] ).replace( regex.dmyreplace, '$2/$1/$3' ) );
					parsed.push( date instanceof Date && isFinite(date) ? date.getTime() : str[i] );
				}
				// sort from min to max
				return parsed.sort().join( ' - ' );
			}
			return text;
		},
		type: 'text'
	});

	/*! date-range DDMMYYYY *//* (2000/2/15 - 2000/5/18) */
	$.tablesorter.addParser({
		id: 'date-range-ymd',
		is: function () {
			return false;
		},
		format: function (text) {
			var date, str, i, len,
				parsed = [];
			str = text.replace( /\s+/g, ' ' ).replace( /[\/\-.,]/g, '-' ).match( regex.ymd );
			len = str && str.length;
			if ( len ) {
				for (i = 0; i < len; i++) {
					date = new Date( ( '' + str[i] ).replace( regex.ymdreplace, '$2/$3/$1' ) );
					parsed.push( date instanceof Date && isFinite(date) ? date.getTime() : str[i] );
				}
				// sort from min to max
				return parsed.sort().join( ' - ' );
			}
			return text;
		},
		type: 'text'
	});

	if ( !ts.dates ) { ts.dates = {}; }
	if ( !ts.dates.months ) { ts.dates.months = {}; }
	ts.dates.months.en = {
		// See http://mottie.github.io/tablesorter/docs/example-widget-grouping.html
		// for details on how to use CLDR data for a locale to add data for this parser
		// CLDR returns an object { 1: "Jan", 2: "Feb", 3: "Mar", ..., 12: "Dec" }
		1 : 'Jan',
		2 : 'Feb',
		3 : 'Mar',
		4 : 'Apr',
		5 : 'May',
		6 : 'Jun',
		7 : 'Jul',
		8 : 'Aug',
		9 : 'Sep',
		10: 'Oct',
		11: 'Nov',
		12: 'Dec'
	};

	getMonthVal = function( str, c, cellIndex ) {
		var m, month,
			// add options to 'config.globalize' for all columns --> globalize : { lang: 'en' }
			// or per column by using the column index --> globalize : { 0 : { lang: 'fr' } }
			options = c.globalize && ( c.globalize[ cellIndex ] || c.globalize ) || {},
			months = ts.dates.months[ options.lang || 'en' ];
		if ( c.ignoreCase ) {
			str = str.toLowerCase();
		}
		for ( month in months ) {
			if ( typeof month === 'string' ) {
				m = months[ month ];
				if ( c.ignoreCase ) {
					m = m.toLowerCase();
				}
				if ( str.match( m ) ) {
					return parseInt( month, 10 );
				}
			}
		}
		return str;
	};

	/*! date-range "dd MMM yyyy - dd MMM yyyy" *//* ( hms optional )*/
	ts.addParser({
		id: 'date-range-dMMMyyyy',
		is: function () {
			return false;
		},
		format: function( text, table, cell, cellIndex ) {
			var date, month, matches, i,
				parsed = [],
				str = text.replace( /\s+/g, ' ' ).match( regex.overall_dMMMyyyy ),
				len = str && str.length;
			if ( len ) {
				for ( i = 0; i < len; i++ ) {
					date = '';
					matches = str[ i ].match( regex.matches_dMMMyyyy );
					if ( matches && matches.length >= 4 ) {
						matches.shift();
						month = getMonthVal( matches[1], table.config, cellIndex );
						if ( !isNaN( month ) ) {
							str[i] = str[i].replace( matches[1], month );
						}
						date = new Date( ( '' + str[ i ] ).replace( ts.regex.shortDateXXY, '$3/$2/$1' ) );
					}
					parsed.push( date instanceof Date && isFinite(date) ? date.getTime() : str[i] );
				}
				// sort from min to max
				return parsed.sort().join( ' - ' );
			}
			return text;
		},
		type: 'text'
	});

})(jQuery);
