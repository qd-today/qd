/*! Widget: sort2Hash (BETA) - updated 9/27/2017 (v2.29.0) */
/* Requires tablesorter v2.8+ and jQuery 1.7+
 * by Rob Garrison
 */
;( function( $ ) {
	'use strict';
	var ts = $.tablesorter || {},
	s2h = ts.sort2Hash = {
		init : function( c, wo ) {
			var filter, temp, page, size,
				table = c.table,
				pager = c.pager,
				hasSaveSort = ts.hasWidget( table, 'saveSort' ),
				sort = s2h.decodeHash( c, wo, 'sort' );
			if ( ( sort && !hasSaveSort ) || ( sort && hasSaveSort && wo.sort2Hash_overrideSaveSort ) ) {
				s2h.convertString2Sort( c, wo, sort );
			}
			if ( ts.hasWidget( c.table, 'pager' ) ) {
				temp = parseInt( s2h.decodeHash( c, wo, 'page' ), 10 );
				page = pager.page = ( temp < 0 ? 0 : ( temp > pager.totalPages ? pager.totalPages - 1 : temp ) );
				size = pager.size = parseInt( s2h.decodeHash( c, wo, 'size' ), 10 );
			}
			if ( ts.hasWidget( table, 'filter' ) ) {
				filter = s2h.decodeHash( c, wo, 'filter' );
				if ( filter ) {
					filter = filter.split( wo.sort2Hash_separator );
					c.$table.one( 'tablesorter-ready', function() {
						setTimeout(function() {
							c.$table.one( 'filterEnd', function() {
								$(this).triggerHandler( 'pageAndSize', [ page, size ] );
							});
							// use the newest filter comparison code
							if ( ts.filter.equalFilters ) {
								temp = ts.filter.equalFilters( c, c.lastSearch, filter );
							} else {
								// quick n' dirty comparison... it will miss filter changes of
								// the same value in a different column, see #1363
								temp = ( c.lastSearch || [] ).join( '' ) !== ( filter || [] ).join( '' );
							}
							// don't set filters if they haven't changed
							if ( !temp ) {
								$.tablesorter.setFilters( table, filter, true );
							}
						}, 100 );
					});
				}
			}
			if ( !filter ) {
				c.$table.one( 'tablesorter-ready', function() {
					c.$table.triggerHandler( 'pageAndSize', [ page, size ] );
				});
			}

			c.$table.on( 'sortEnd.sort2hash filterEnd.sort2hash pagerComplete.sort2Hash', function() {
				if ( this.hasInitialized ) {
					s2h.setHash( this.config, this.config.widgetOptions );
				}
			});
		},

		getTableId : function( c, wo ) {
			// option > table id > table index on page
			return wo.sort2Hash_tableId ||
				c.table.id ||
				'table' + $( 'table' ).index( c.$table );
		},
		regexEscape : function( v ) {
			return v.replace( /([\.\^\$\*\+\-\?\(\)\[\]\{\}\\\|])/g, '\\$1');
		},
		// convert 'first%20name,asc,last%20name,desc' into [[0,0], [1,1]]
		convertString2Sort : function( c, wo, sortHash ) {
			var regex, column, direction, temp, index, $cell,
				arry = sortHash.split( wo.sort2Hash_separator ),
				indx = 0,
				len = arry.length,
				sort = [];
			while ( indx < len ) {
				// column index or text
				column = arry[ indx++ ];
				temp = parseInt( column, 10 );
				// ignore wo.sort2Hash_useHeaderText setting &
				// just see if column contains a number
				if ( isNaN( temp ) || temp > c.columns ) {
					regex = new RegExp( '(' + s2h.regexEscape( column ) + ')', 'i' );
					for ( index = 0; index < c.columns; index++ ) {
						$cell = c.$headerIndexed[ index ];
						if ( regex.test( $cell.attr( wo.sort2Hash_headerTextAttr ) ) ) {
							column = index;
							index = c.columns;
						}
					}
				}
				direction = arry[ indx++ ];
				// ignore unpaired values
				if ( typeof column !== 'undefined' && typeof direction !== 'undefined' ) {
					// convert text to 0, 1
					if ( isNaN( direction ) ) {
						// default to ascending sort
						direction = direction.indexOf( wo.sort2Hash_directionText[ 1 ] ) > -1 ? 1 : 0;
					}
					sort.push( [ column, direction ] );
				}
			}
			if ( sort.length ) {
				c.sortList = sort;
			}
		},

		// convert [[0,0],[1,1]] to 'first%20name,asc,last%20name,desc'
		convertSort2String : function( c, wo ) {
			var index, txt, column, direction,
				sort = [],
				arry = c.sortList || [],
				len = arry.length;
			for ( index = 0; index < len; index++ ) {
				column = arry[ index ][ 0 ];
				txt = $.trim( c.$headerIndexed[ column ].attr( wo.sort2Hash_headerTextAttr ) );
				sort.push( txt !== '' ? encodeURIComponent( txt ) : column );
				direction = wo.sort2Hash_directionText[ arry[ index ][ 1 ] ];
				sort.push( direction );
			}
			// join with separator
			return sort.join( wo.sort2Hash_separator );
		},

		convertFilter2String : function( c, wo ) {
			var index, txt, column, direction,
				sort = [],
				arry = c.sortList || [],
				len = arry.length;
			for ( index = 0; index < len; index++ ) {
				column = arry[ index ][ 0 ];
				txt = $.trim( c.$headerIndexed[ column ].attr( wo.sort2Hash_headerTextAttr ) );
				column = typeof txt !== 'undefined' ? encodeURIComponent( txt ) : column;
				sort.push( column );
				direction = wo.sort2Hash_directionText[ arry[ index ][ 1 ] ];
				sort.push( direction );
			}
			// join with separator
			return sort.join( wo.sort2Hash_separator );
		},

		// Get URL Parameters (getParam)
		// modified from http://www.netlobo.com/url_query_string_javascript.html
		getParam : function ( name, hash, returnRegex ) {
			if ( !hash ) { hash = window.location.hash; }
			var regex = new RegExp( '[\\?&]' + s2h.regexEscape( name ) + '=([^&#]*)' ),
				match = regex.exec( hash );
			if ( returnRegex ) { return regex; }
			return match === null ? '' : decodeURIComponent( match[ 1 ] );
		},

		// remove parameter from hash
		removeParam : function( name, hash ) {
			if ( !hash ) { hash = window.location.hash; }
			var index,
				regex = s2h.getParam( name, hash, true ),
				result = [],
				parts = hash.split( '&' ),
				len = parts.length;
			for ( index = 0; index < len; index++ ) {
				// regex expects a leading '&'...
				if ( !regex.test( '&' + parts[ index ] ) ) {
					result.push( parts[ index ] );
				}
			}
			return result.length ? result.join( '&' ) : '';
		},

		encodeHash : function( c, wo, component, value, rawValue ) {
			var result = false,
				tableId = s2h.getTableId( c, wo );
			if ( typeof wo.sort2Hash_encodeHash === 'function' ) {
				result = wo.sort2Hash_encodeHash( c, tableId, component, value, rawValue || value );
			}
			if ( result === false ) {
				result = '&' + component + '[' + tableId + ']=' + value;
			}
			return result;
		},

		decodeHash : function( c, wo, component ) {
			var result = false,
				tableId = s2h.getTableId( c, wo );
			if ( typeof wo.sort2Hash_decodeHash === 'function' ) {
				// return a string
				result = wo.sort2Hash_decodeHash( c, tableId, component );
			}
			if ( result === false ) {
				result = s2h.getParam( component + '[' + tableId + ']' );
			}
			return result || '';
		},

		cleanHash : function( c, wo, component, hash ) {
			var result = false,
				tableId = s2h.getTableId( c, wo );
			if ( typeof wo.sort2Hash_cleanHash === 'function' ) {
				// can return an array or string
				result = wo.sort2Hash_cleanHash( c, tableId, component, hash );
			}
			if ( result === false ) {
				// parameter example: 'sort[table0]=0,0'
				result = s2h.removeParam( component + '[' + tableId + ']', hash );
			}
			return result || '';
		},

		setHash : function( c, wo ) {
			var str = '',
				hash = window.location.hash,
				hasPager = ts.hasWidget( c.table, 'pager' ),
				hasFilter = ts.hasWidget( c.table, 'filter' ),
				sortList = s2h.convertSort2String( c, wo ),
				filters = ( hasFilter && c.lastSearch.join('') !== '' ? c.lastSearch : [] ),
				filtersStr = encodeURIComponent( filters.join( c.widgetOptions.sort2Hash_separator ) ),
				components = {
					'sort'   : sortList ? s2h.encodeHash( c, wo, 'sort', sortList, c.sortList ) : '',
					'page'   : hasPager ? s2h.encodeHash( c, wo, 'page', c.pager.page + 1 ) : '',
					'size'   : hasPager ? s2h.encodeHash( c, wo, 'size', c.pager.size ) : '',
					'filter' : filtersStr ? s2h.encodeHash( c, wo, 'filter', filtersStr, filters ) : ''
				};
			// remove old hash
			$.each( components, function( component, value ) {
				hash = s2h.cleanHash( c, wo, component, hash );
				str += value;
			});

			var hashChar = wo.sort2Hash_hash;
			// Combine new hash with any existing hashes
			var newHash = (
				( window.location.hash || '' ).replace( hashChar, '' ).length ?
				hash : hashChar
			) + str;

			if (wo.sort2Hash_replaceHistory) {
				var baseUrl = window.location.href.split(hashChar)[0];
				// Ensure that there is a leading hash character
				var firstChar = newHash[0];
				if (firstChar !== hashChar) {
					newHash = hashChar + newHash;
				}
				// Update URL in browser
				window.location.replace(baseUrl + newHash);
			} else {
				// Add updated hash
				window.location.hash = newHash;
			}
		}
	};

	ts.addWidget({
		id: 'sort2Hash',
		priority: 60, // after saveSort & pager
		options: {
			sort2Hash_hash              : '#',      // hash prefix
			sort2Hash_separator         : '-',      // don't '#' or '=' here
			sort2Hash_headerTextAttr    : 'data-header', // data attribute containing alternate header text
			sort2Hash_directionText     : [ 0, 1 ], // [ 'asc', 'desc' ],
			sort2Hash_overrideSaveSort  : false,    // if true, override saveSort widget if saved sort available
			sort2Hash_replaceHistory    : false,    // if true, hash changes are not saved to browser history

			// this option > table ID > table index on page
			sort2Hash_tableId           : null,
			// custom hash processing functions
			sort2Hash_encodeHash        : null,
			sort2Hash_decodeHash        : null,
			sort2Hash_cleanHash         : null
		},
		init: function(table, thisWidget, c, wo) {
			s2h.init( c, wo );
		},
		remove: function(table, c) {
			c.$table.off( '.sort2hash' );
		}
	});

})(jQuery);
