/*! Widget: mark.js - updated 9/23/2016 (v2.27.7) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * by Rob Garrison
 */
;( function( $ ) {
	'use strict';
	var ts = $.tablesorter;

	ts.mark = {
		init : function( c ) {
			if ( typeof $.fn.mark === 'function' ) {
				var tmp,
					update = c.widgetOptions.mark_tsUpdate;
				c.$table.on( 'filterEnd.tsmark pagerComplete.tsmark' +
					( update ? ' ' + update : '' ), function( e, filters ) {
					// filterEnd passes "config" as the param
					ts.mark.update( c, e.type === update ? filters : '' );
				});
				// Regex to split up a query
				tmp = '(?:<|=|>|\\||\"|' + "\\'|" +
					'\\s+(?:&&|-|' +
					( ts.language.and || 'and' ) + '|' +
					( ts.language.or || 'or' ) + '|' +
					( ts.language.to || 'to' ) + ')\\s+)';
				ts.mark.regex.filter = new RegExp(tmp, 'gim');
			} else {
				console.warn('Widget-mark not initialized: missing "jquery.mark.js"');
			}
		},
		regex : {
			mark : /^mark_(.+)$/,
			// test for regex (e.g. "/(lorem|ipsum)/gi")
			pure : /^\/((?:\\\/|[^\/])+)\/([mig]{0,3})?$/
		},
		checkRegex : function( regex ) {
			if ( regex instanceof RegExp ) {
				// prevent lock up of mark.js
				// (see https://github.com/julmot/mark.js/issues/55)
				var result = '\u0001\u0002\u0003\u0004\u0005'.match( regex );
				return result === null || result.length < 5;
			}
			return false;
		},
		cleanMatches : function( matches ) {
			var results = [],
				indx = matches && matches.length || 0;
			while ( indx-- ) {
				if ( matches[indx] !== '' ) {
					results[ results.length ] = matches[ indx ];
				}
			}
			return results;
		},
		// used when "any" match is performed
		ignoreColumns : function( c ) {
			var wo = c.widgetOptions,
				len = c.columns,
				cols = [];
			while (len--) {
				if (wo.mark_tsIgnore[len] ||
					$( c.$headerIndexed[len] ).hasClass( 'mark-ignore' ) ) {
					cols[cols.length] = ':nth-child(' + (len + 1) + ')';
				}
			}
			if (cols.length) {
				return ':not(' + cols.join(',') + ')';
			}
			return '';
		},
		update : function( c, filters ) {
			var options = {},
				wo = c.widgetOptions,
				regex = ts.mark.regex,
				$rows = c.$table
					.find( 'tbody tr' )
					.unmark()
					.not( '.' + ( c.widgetOptions.filter_filteredRow || 'filtered' ) );
			filters = filters || $.tablesorter.getFilters( c.$table );
			// extract & save mark options from widgetOptions (prefixed with "mark_")
			// update dynamically
			$.each( c.widgetOptions, function( key, val ) {
				var matches = key.match( regex.mark );
				if ( matches && typeof matches[1] !== 'undefined' ) {
					options[ matches[1] ] = val;
				}
			});
			$.each( filters, function( indx, filter ) {
				if ( filter &&
					!( $(c.$headerIndexed[indx]).hasClass('mark-ignore') ||
						wo.mark_tsIgnore[indx]
					) ) {
					var testRegex = null,
						matches = filter,
						useRegex = false,
						col = indx === c.columns ?
							ts.mark.ignoreColumns( c ) :
							':nth-child(' + ( indx + 1 ) + ')';
					// regular expression entered
					if ( regex.pure.test( filter ) ) {
						matches = regex.pure.exec( filter );
						// ignore "all" matches (i.e. /.*/)
						if (matches[1] === '.*') {
							matches[1] = '';
						}
						try {
							// make sure to include global flag when testing regex
							testRegex = new RegExp( matches[ 1 ], 'gim' );
							matches = new RegExp( matches[ 1 ], matches[ 2 ] );
						} catch (err) {
							matches = null;
						}
						if ( ts.mark.checkRegex( testRegex ) ) {
							$rows.children( col ).markRegExp( matches, options );
						}
						// matches is either null, invalid, or done my markRegExp
						return;
					}
					// all special querys (or, and, wild cards & fuzzy)
					// regex seems to not be consistent here; so use string indexOf
					// fuzzy or wild card matches
					if ( filter.indexOf( '~' ) === 0 ) {
						useRegex = true;
						// fuzzy search separate each letter
						matches = filter.replace( /~/g, '' ).split( '' );
					} else {
						// wild card matching
						if ( filter.indexOf( '?' ) > -1 ) {
							useRegex = true;
							filter = filter.replace( /\?/g, '\\S{1}' );
						}
						if ( filter.indexOf( '*' ) > -1 ) {
							useRegex = true;
							filter = filter.replace( /\*/g, '\\S*' );
						}
						matches = filter.split( regex.filter );
					}
					if ( useRegex && matches && matches.length ) {
						matches = new RegExp(
							ts.mark.cleanMatches( matches ).join( '.*' ),
							'gm'
						);
						if ( ts.mark.checkRegex( matches ) ) {
							$rows.children( col ).markRegExp( matches, options );
						}
					} else {
						// pass an array of matches
						$rows.children( col ).mark(
							ts.mark.cleanMatches( matches ),
							options
						);
					}
				}
			});
		}
	};

	ts.addWidget({
		id: 'mark',
		options: {
			mark_tsUpdate : 'markUpdate',
			mark_tsIgnore : {}
		},
		init : function( table, thisWidget, c, wo ) {
			ts.mark.init( c, wo );
		},
		remove : function( table, c ) {
			var update = c.widgetOptions.mark_tsUpdate;
			c.$table.off( 'filterEnd.tsmark pagerComplete.tsmark' +
				( update ? ' ' + update : '' ) );
		}
	});

})( jQuery );
