/*! Widget: currentSort - 7/31/2016 (v2.27.0) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * by Rob Garrison
 */
;( function( $ ) {
	'use strict';
	var ts = $.tablesorter;

	ts.currentSortLanguage = {
		0: 'asc',
		1: 'desc',
		2: 'unsorted'
	};

	ts.currentSort = {
		init : function( c ) {
			c.$table.on( 'sortEnd.tscurrentSort', function() {
				ts.currentSort.update( this.config );
			});
		},
		update: function( c ) {
			if ( c ) {
				var indx,
					wo = c.widgetOptions,
					lang = ts.currentSortLanguage,
					unsort = lang[ 2 ],
					// see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/fill
					// order = new Array(c.columns).fill(unsort),
					// the above ES6 will not work in all browsers, so
					// we're stuck with this messy code to fill the array:
					order = Array
						.apply( null, Array( c.columns ) )
						.map( String.prototype.valueOf, unsort ),
						sortList = c.sortList,
					len = sortList.length;
				for ( indx = 0; indx < len; indx++ ) {
					order[ sortList[ indx ][ 0 ] ] = lang[ sortList[ indx ][ 1 ] ];
				}
				c.currentSort = order;
				if ( typeof wo.currentSort_callback === 'function' ) {
					wo.currentSort_callback(c, order);
				}
			}
		}
	};

	ts.addWidget({
		id: 'currentSort',
		options: {
			currentSort_callback : null
		},
		init : function( table, thisWidget, c, wo ) {
			ts.currentSort.init( c, wo );
		},
		remove : function( table, c ) {
			c.$table.off( 'sortEnd.tscurrentSort' );
		}
	});

})( jQuery );
