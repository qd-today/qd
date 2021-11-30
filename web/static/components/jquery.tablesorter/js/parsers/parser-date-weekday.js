/*! Parser: weekday - updated 11/22/2015 (v2.24.6) */
/* Demo: http://jsfiddle.net/Mottie/abkNM/4169/ */
/*jshint jquery:true */
;(function($) {
	'use strict';

	var ts = $.tablesorter;

	if ( !ts.dates ) { ts.dates = {}; }
	if ( !ts.dates.weekdays ) { ts.dates.weekdays = {}; }
	// See http://mottie.github.io/tablesorter/docs/example-widget-grouping.html
	// for details on how to use CLDR data for a locale to add data for this parser
	// CLDR returns { sun: "Sun", mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", ... }
	ts.dates.weekdays.en = {
		'sun' : 'Sun',
		'mon' : 'Mon',
		'tue' : 'Tue',
		'wed' : 'Wed',
		'thu' : 'Thu',
		'fri' : 'Fri',
		'sat' : 'Sat'
	};
	// set table.config.weekStarts to change weekday start date for your locale
	// cross-reference of a date on which the week starts on a...
	// https://github.com/unicode-cldr/cldr-core/blob/master/supplemental/weekData.json
	// locale agnostic
	ts.dates.weekStartList = {
		'sun' : '1995', // Sun 1/1/1995
		'mon' : '1996', // Mon 1/1/1996
		'fri' : '1999', // Friday 1/1/1999
		'sat' : '2000'  // Sat 1/1/2000
	};
	// do not modify this array; it is used for cross referencing weekdays
	// locale agnostic
	ts.dates.weekdaysXref = [ 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat' ];

	ts.addParser({
		id: 'weekday',
		is: function() {
			return false;
		},
		format: function( str, table, cell, cellIndex ) {
			if ( str ) {
				var d, day, num,
					c = table.config,
					// add options to 'config.globalize' for all columns --> globalize : { lang: 'en' }
					// or per column by using the column index --> globalize : { 0 : { lang: 'fr' } }
					options = c.globalize && ( c.globalize[ cellIndex ] || c.globalize ) || {},
					days = ts.dates.weekdays[ options.lang || 'en' ],
					xref = ts.dates.weekdaysXref;
				if ( c.ignoreCase ) {
					str = str.toLowerCase();
				}
				for ( day in days ) {
					if ( typeof day === 'string' ) {
						d = days[ day ];
						if ( c.ignoreCase ) {
							d = d.toLowerCase();
						}
						if ( str.match( d ) ) {
							num = $.inArray( day, xref );
							return num > -1 ? num : str;
						}
					}
				}
			}
			return str;
		},
		type: 'numeric'
	});

	// useful when a group widget date column is set to "group-date-week"
	// and you want to only sort on the day of the week ignore the actual date, month and year
	ts.addParser({
		id: 'weekday-index',
		is: function() {
			return false;
		},
		format: function( str, table ) {
			if ( str ) {
				var c = table.config,
					date = new Date( str );
				if ( date instanceof Date && isFinite( date ) ) {
					// use a specific date that started with that weekday so sorting is only going to be
					// based on the day of the week and not the date, month or year
					return new Date( '1/' + ( date.getDay() + 1 ) + '/' + ts.dates.weekStartList[ c.weekStarts || 'sun' ] );
				}
			}
			return str;
		},
		type: 'numeric'
	});

})(jQuery);
