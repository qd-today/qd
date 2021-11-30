/*! Widget: math - updated 12/1/2019 (v2.31.2) *//*
* Requires tablesorter v2.16+ and jQuery 1.7+
* by Rob Garrison
*/
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery: false */
;( function( $ ) {
	'use strict';

	var ts = $.tablesorter,

	math = {

		error: {
			0       : 'Infinity result: Divide by zero',
			1       : 'Need more than one element to make this calculation',
			'undef' : 'No elements found'
		},

		// value returned when calculation is not possible, e.g. no values, dividing by zero, etc.
		invalid : function( c, name, errorIndex ) {
			// name = function returning invalid results
			// errorIndex = math.error index with an explanation of the error
			console.warn( name, math.error[ errorIndex ] );
			return c && c.widgetOptions.math_none || ''; // text for cell
		},

		events : ( 'tablesorter-initialized update updateAll updateRows addRows updateCell filterReset ' )
			.split(' ').join('.tsmath '),

		processText : function( c, $cell ) {
			var tmp,
				wo = c.widgetOptions,
				txt = ts.getElementText( c, $cell, math.getCellIndex( $cell ) ),
				prefix = c.widgetOptions.math_prefix;
			if (wo.math_textAttr) {
				txt = $cell.attr(wo.math_textAttr) || txt;
			}
			if ( /</.test( prefix ) ) {
				// prefix contains HTML; remove it & any text before using formatFloat
				tmp = $( '<div>' + prefix + '</div>' ).text()
					.replace(/\{content\}/g, '').trim();
				txt = txt.replace( tmp, '' );
			}
			txt = ts.formatFloat( txt.replace( /[^\w,. \-()]/g, '' ), c.table ) || 0;
			// isNaN('') => false
			return isNaN( txt ) ? 0 : txt;
		},

		// get all of the row numerical values in an arry
		getRow : function( c, $el, hasFilter ) {
			var $cells,
				wo = c.widgetOptions,
				arry = [],
				$row = $el.closest( 'tr' ),
				isFiltered = $row.hasClass( wo.filter_filteredRow || 'filtered' );
			if ( hasFilter ) {
				$row = $row.filter( hasFilter );
			}
			if ( hasFilter || !isFiltered ) {
				$cells = $row.children().not( '[' + wo.math_dataAttrib + '=ignore]' );
				if ( wo.math_ignore.length ) {
					$cells = $cells.filter( function() {
						// using $.inArray is not optimal (needed for IE8)
						return $.inArray( math.getCellIndex( $( this ) ), wo.math_ignore ) === -1;
					});
				}
				arry = $cells.not( $el ).map( function() {
					return math.processText( c, $( this ) );
				}).get();
			}
			return arry;
		},

		// get all of the column numerical values in an arry
		getColumn : function( c, $el, type, hasFilter ) {
			var index, $t, $tr, len, $mathRows, mathAbove,
				wo = c.widgetOptions,
				arry = [],
				$row = $el.closest( 'tr' ),
				mathAttr = wo.math_dataAttrib,
				mathIgnore = '[' + mathAttr + '=ignore]',
				filtered = wo.filter_filteredRow || 'filtered',
				cIndex = math.getCellIndex( $el ),
				// get all rows to keep row indexing
				$rows = c.$table.children( 'tbody' ).children(),
				mathAttrs = [
					'[' + mathAttr + '^=above]',
					'[' + mathAttr + '^=below]',
					'[' + mathAttr + '^=col]',
					'[' + mathAttr + '^=all]'
				];
			if ( type === 'above' ) {
				len = $rows.index( $row );
				index = len;
				while ( index >= 0 ) {
					$tr = $rows.eq( index );
					mathAbove = $tr.children().filter( mathAttrs[0] ).length;
					if ( hasFilter ) {
						$tr = $tr.filter( hasFilter );
					}
					$t = $tr.children().filter( function() {
						return math.getCellIndex( $( this ) ) === cIndex;
					});
					// ignore filtered rows & rows with data-math="ignore" (and starting row)
					if ( ( ( hasFilter || !$tr.hasClass( filtered ) ) &&
							$tr.not( mathIgnore ).length &&
							index !== len ) ||
							mathAbove && index !== len ) {
						// stop calculating 'above', when encountering another 'above'
						if ( mathAbove ) {
							index = 0;
						} else if ( $t.length && $t.not( mathIgnore ).length ) {
							arry[ arry.length ] = math.processText( c, $t );
						}
					}
					index--;
				}
			} else if ( type === 'below' ) {
				len = $rows.length;
				// index + 1 to ignore starting node
				for ( index = $rows.index( $row ) + 1; index < len; index++ ) {
					$tr = $rows.eq( index );
					if ( $tr.children().filter( mathAttrs[1] ).length ) {
						break;
					}
					if ( hasFilter ) {
						$tr = $tr.filter( hasFilter );
					}
					$t = $tr.children().filter( function() {
						return math.getCellIndex( $( this ) ) === cIndex;
					});
					if ( ( hasFilter || !$tr.hasClass( filtered ) ) &&
						$tr.not( mathIgnore ).length &&
						$t.length && $t.not( mathIgnore ) ) {
						arry[ arry.length ] = math.processText( c, $t );
					}
				}
			} else {
				$mathRows = $rows.not( mathIgnore );
				len = $mathRows.length;
				for ( index = 0; index < len; index++ ) {
					$tr = $mathRows.eq( index );
					if ( hasFilter ) {
						$tr = $tr.filter( hasFilter );
					}
					$t = $tr.children().filter( function() {
						return math.getCellIndex( $( this ) ) === cIndex;
					});
					if ( ( hasFilter || !$tr.hasClass( filtered ) ) &&
						$t.not( mathAttrs.join( ',' ) ).length &&
						!$t.is( $el ) && $t.not( mathIgnore ).length
					) {
						arry[ arry.length ] = math.processText( c, $t );
					}
				}
			}
			return arry;
		},

		// get all of the column numerical values in an arry
		getAll : function( c, hasFilter ) {
			var $t, col, $row, rowIndex, rowLen, $cells, cellIndex, cellLen,
				arry = [],
				wo = c.widgetOptions,
				mathAttr = wo.math_dataAttrib,
				mathIgnore = '[' + mathAttr + '=ignore]',
				filtered = wo.filter_filteredRow || 'filtered',
				$rows = c.$table.children( 'tbody' ).children().not( mathIgnore );
			rowLen = $rows.length;
			for ( rowIndex = 0; rowIndex < rowLen; rowIndex++ ) {
				$row = $rows.eq( rowIndex );
				if ( hasFilter ) {
					$row = $row.filter( hasFilter );
				}
				if ( hasFilter || !$row.hasClass( filtered ) ) {
					$cells = $row.children().not( mathIgnore );
					cellLen = $cells.length;
					for ( cellIndex = 0; cellIndex < cellLen; cellIndex++ ) {
						$t = $cells.eq( cellIndex );
						col = math.getCellIndex( $t );
						if ( !$t.filter( '[' + mathAttr + ']' ).length && $.inArray( col, wo.math_ignore ) < 0 ) {
							arry[ arry.length ] = math.processText( c, $t );
						}
					}
				}
			}
			return arry;
		},

		setColumnIndexes : function( c ) {
			var $table = c.$table,
				last = 1,
				// only target rows with a colspan or rows included in a rowspan
				$rows = $table.children( 'tbody' ).children().filter( function() {
					var cells, indx,
						$this = $( this ),
						include = $this.children( '[colspan]' ).length > 0;
					if ( last > 1 ) {
						last--;
						include = true;
					} else if ( last < 1 ) {
						last = 1;
					}
					if ( $this.children( '[rowspan]' ).length > 0 ) {
						cells = this.cells;
						// find max rowspan (in case more than one cell has a rowspan)
						for ( indx = 0; indx < cells.length; indx++ ) {
							last = Math.max( cells[ indx ].rowSpan, last );
						}
					}
					return include;
				});
			// pass `c` (table.config) to computeColumnIndex so it won't add a data-column
			// to every tbody cell, just the ones where the .cellIndex property doesn't match
			// the calculated cell index - hopefully fixes the lag issue in #1048
			ts.computeColumnIndex( $rows, c );
		},

		getCellIndex : function( $cell ) {
			var indx = $cell.attr( 'data-column' );
			return typeof indx === 'undefined' ? $cell[0].cellIndex : parseInt( indx, 10 );
		},

		recalculate : function(c, wo, init) {
			if ( c && ( !wo.math_isUpdating || init ) ) {

				var time, mathAttr, $mathCells, indx, len,
					changed = false,
					filters = {};
				if ( c.debug || wo.math_debug ) {
					time = new Date();
				}

				// add data-column attributes to all table cells
				if ( init ) {
					math.setColumnIndexes( c ) ;
				}

				// data-attribute name (defaults to data-math)
				wo.math_dataAttrib = 'data-' + (wo.math_data || 'math');

				// all non-info tbody cells
				mathAttr = wo.math_dataAttrib;
				$mathCells = c.$tbodies.children( 'tr' ).children( '[' + mathAttr + ']' );
				changed = math.mathType( c, $mathCells, wo.math_priority ) || changed;
				// only info tbody cells
				$mathCells = c.$table
					.children( '.' + c.cssInfoBlock + ', tfoot' )
					.children( 'tr' )
					.children( '[' + mathAttr + ']' );
				math.mathType( c, $mathCells, wo.math_priority );

				// find the 'all' total
				$mathCells = c.$table.children().children( 'tr' ).children( '[' + mathAttr + '^=all]' );
				len = $mathCells.length;
				// get math filter, if any
				// hasFilter = $row.attr( mathAttr + '-filter' ) || wo.math_rowFilter;
				for (indx = 0; indx < len; indx++) {
					var $cell = $mathCells.eq( indx ),
						filter = $cell.attr( mathAttr + '-filter' ) || wo.math_rowFilter;
					filters[ filter ] = filters[ filter ] ? filters[ filter ].add( $cell ) : $cell;
				}
				$.each( filters, function( hasFilter, $cells ) {
					changed = math.mathType( c, $cells, [ 'all' ], hasFilter ) || changed;
				});

				// trigger an update only if cells inside the tbody changed
				if ( changed ) {
					wo.math_isUpdating = true;
					if ( c.debug || wo.math_debug ) {
						console[ console.group ? 'group' : 'log' ]( 'Math widget updating the cache after recalculation' );
					}

					// update internal cache, but ignore "remove-me" rows and do not resort
					ts.updateCache( c, function() {
						math.updateComplete( c );
						if ( !init && typeof wo.math_completed === 'function' ) {
							wo.math_completed( c );
						}
						if ( c.debug || wo.math_debug ) {
							console.log( 'Math widget update completed' + ts.benchmark( time ) );
						}
					});
				} else {
					if ( !init && typeof wo.math_completed === 'function' ) {
						wo.math_completed( c );
					}
					if ( c.debug || wo.math_debug ) {
						console.log( 'Math widget found no changes in data' + ts.benchmark( time ) );
					}
				}
			}
		},

		updateComplete : function( c ) {
			var wo = c.widgetOptions;
			if ( wo.math_isUpdating && (c.debug || wo.math_debug ) && console.groupEnd ) {
				console.groupEnd();
			}
			wo.math_isUpdating = false;
		},

		mathType : function( c, $cells, priority, hasFilter ) {
			if ( $cells.length ) {
				var getAll,
					changed = false,
					wo = c.widgetOptions,
					mathAttr = wo.math_dataAttrib,
					equations = ts.equations;
				if ( priority[0] === 'all' ) {
					// mathType is called multiple times if more than one "hasFilter" is used
					getAll = math.getAll( c, hasFilter );
				}
				if (c.debug || wo.math_debug) {
					console[ console.group ? 'group' : 'log' ]( 'Tablesorter Math widget recalculation' );
				}
				// $.each is okay here... only 4 priorities
				$.each( priority, function( i, type ) {
					var index, arry, formula, result, $el,
						$targetCells = $cells.filter( '[' + mathAttr + '^=' + type + ']' ),
						len = $targetCells.length;
					if ( len ) {
						if (c.debug || wo.math_debug) {
							console[ console.group ? 'group' : 'log' ]( type );
						}
						for ( index = 0; index < len; index++ ) {
							$el = $targetCells.eq( index );
							// Row is filtered, no need to do further checking
							if ( $el.parent().hasClass( wo.filter_filteredRow || 'filtered' ) ) {
								continue;
							}
							hasFilter = $el.attr( mathAttr + '-filter' ) || wo.math_rowFilter;
							formula = ( $el.attr( mathAttr ) || '' ).replace( type + '-', '' );
							arry = ( type === 'row' ) ? math.getRow( c, $el, hasFilter ) :
								( type === 'all' ) ? getAll : math.getColumn( c, $el, type, hasFilter );
							if ( equations[ formula ] ) {
								if ( arry.length ) {
									result = equations[ formula ]( arry, c );
									if ( c.debug || wo.math_debug ) {
										console.log( $el.attr( mathAttr ), hasFilter ? '("' + hasFilter + '")' : '', arry, '=', result );
									}
								} else {
									// mean will return a divide by zero error, everything else shows an undefined error
									result = math.invalid( c, formula, formula === 'mean' ? 0 : 'undef' );
								}
								changed = math.output( $el, c, result, arry ) || changed;
							}
						}
						if ( ( c.debug || wo.math_debug ) && console.groupEnd ) { console.groupEnd(); }
					}
				});
				if ( ( c.debug || wo.math_debug ) && console.groupEnd ) { console.groupEnd(); }
				return changed;
			}
			return false;
		},

		output : function( $cell, c, value, arry ) {
			// get mask from cell data-attribute: data-math-mask="#,##0.00"
			var $el,
				wo = c.widgetOptions,
				changed = false,
				prev = $cell.html(),
				mask = $cell.attr( 'data-' + wo.math_data + '-mask' ) || wo.math_mask,
				target = $cell.attr( 'data-' + wo.math_data + '-target' ) || '',
				result = ts.formatMask( mask, value, wo.math_prefix, wo.math_suffix );
			if (target) {
				$el = $cell.find(target);
				if ($el.length) {
					$cell = $el;
				}
			}
			if ( typeof wo.math_complete === 'function' ) {
				result = wo.math_complete( $cell, wo, result, value, arry );
			}
			if ( result !== false ) {
				changed = prev !== result;
				$cell.html( result );
			}
			// check if in a regular tbody, otherwise don't pass a changed flag
			// to prevent unnecessary updating of the table cache
			if ( changed ) {
				$el = $cell.closest( 'tbody' );
				// content was changed in a tfoot, info-only tbody or the resulting tbody is in a nested table
				// then don't signal a change
				if ( !$el.length || $el.hasClass( c.cssInfoBlock ) || $el.parent()[0] !== c.table ) {
					return false;
				}
			}
			return changed;
		}

	};

	// Modified from https://code.google.com/p/javascript-number-formatter/
	/**
	* @preserve IntegraXor Web SCADA - JavaScript Number Formatter
	* http:// www.integraxor.com/
	* author: KPL, KHL
	* (c)2011 ecava
	* Dual licensed under the MIT or GPL Version 2 licenses.
	*/
	ts.formatMask = function( mask, val, tmpPrefix, tmpSuffix ) {
		if ( !mask || isNaN( +val ) ) {
			return val; // return as it is.
		}

		var isNegative, result, decimal, group, posLeadZero, posTrailZero, posSeparator, part, szSep,
			integer, str, offset, index, end, inv,
			suffix = '',

			// find prefix/suffix
			len = mask.length,
			start = mask.search( /[0-9\-\+#]/ ),
			tmp = start > 0 ? mask.substring( 0, start ) : '',
			prefix = tmp;
		if ( tmpPrefix ) {
			if ( /\{content\}/.test( tmpPrefix || '' ) ) {
				prefix = ( tmpPrefix || '' ).replace( /\{content\}/g, tmp || '' );
			} else {
				prefix = ( tmpPrefix || '' ) + tmp;
			}
		}
		// reverse string: not an ideal method if there are surrogate pairs
		inv = mask.split( '' ).reverse().join( '' );
		end = inv.search( /[0-9\-\+#]/ );
		index = len - end;
		index += ( mask.substring( index, index + 1 ) === '.' ) ? 1 : 0;
		tmp = end > 0 ? mask.substring( index, len ) : '';
		suffix = tmp;
		if ( tmpSuffix ) {
			if ( /\{content\}/.test( tmpSuffix || '' ) ) {
				suffix = ( tmpSuffix || '' ).replace( /\{content\}/g, tmp || '' );
			} else {
				suffix = tmp + ( tmpSuffix || '' );
			}
		}
		mask = mask.substring( start, index );

		// convert any string to number according to formation sign.
		val = mask.charAt( 0 ) === '-' ? -val : +val;
		isNegative = val < 0 ? val = -val : 0; // process only abs(), and turn on flag.

		// search for separator for grp & decimal, anything not digit, not +/- sign, not #.
		result = mask.match( /[^\d\-\+#]/g );
		decimal = ( result && result[ result.length - 1 ] ) || '.'; // treat the right most symbol as decimal
		group = ( result && result[ 1 ] && result[ 0 ] ) || ',';  // treat the left most symbol as group separator

		// split the decimal for the format string if any.
		mask = mask.split( decimal );
		// Fix the decimal first, toFixed will auto fill trailing zero.
		val = val.toFixed( mask[ 1 ] && mask[ 1 ].length );
		val = +( val ) + ''; // convert number to string to trim off *all* trailing decimal zero(es)

		// fill back any trailing zero according to format
		posTrailZero = mask[ 1 ] && mask[ 1 ].lastIndexOf( '0' ); // look for last zero in format
		part = val.split( '.' );
		// integer will get !part[1]
		if ( !part[ 1 ] || ( part[ 1 ] && part[ 1 ].length <= posTrailZero ) ) {
			val = ( +val ).toFixed( posTrailZero + 1 );
		}
		szSep = mask[ 0 ].split( group ); // look for separator
		mask[ 0 ] = szSep.join( '' ); // join back without separator for counting the pos of any leading 0.

		posLeadZero = mask[ 0 ] && mask[ 0 ].indexOf( '0' );
		if ( posLeadZero > -1 ) {
			while ( part[ 0 ].length < ( mask[ 0 ].length - posLeadZero ) ) {
				part[ 0 ] = '0' + part[ 0 ];
			}
		} else if ( +part[ 0 ] === 0 ) {
			part[ 0 ] = '';
		}

		val = val.split( '.' );
		val[ 0 ] = part[ 0 ];

		// process the first group separator from decimal (.) only, the rest ignore.
		// get the length of the last slice of split result.
		posSeparator = ( szSep[ 1 ] && szSep[ szSep.length - 1 ].length );
		if ( posSeparator ) {
			integer = val[ 0 ];
			str = '';
			offset = integer.length % posSeparator;
			len = integer.length;
			for ( index = 0; index < len; index++ ) {
				str += integer.charAt( index ); // ie6 only support charAt for sz.
				// -posSeparator so that won't trail separator on full length
				/*jshint -W018 */
				if ( !( ( index - offset + 1 ) % posSeparator ) && index < len - posSeparator ) {
					str += group;
				}
			}
			val[ 0 ] = str;
		}

		val[ 1 ] = ( mask[ 1 ] && val[ 1 ] ) ? decimal + val[ 1 ] : '';
		// put back any negation, combine integer and fraction, and add back prefix & suffix
		return prefix + ( ( isNegative ? '-' : '' ) + val[ 0 ] + val[ 1 ] ) + suffix;
	};

	ts.equations = {
		count : function( arry ) {
			return arry.length;
		},
		sum : function( arry ) {
			var index,
				len = arry.length,
				total = 0;
			for ( index = 0; index < len; index++ ) {
				total += arry[ index ];
			}
			return total;
		},
		mean : function( arry ) {
			var total = ts.equations.sum( arry );
			return total / arry.length;
		},
		median : function( arry, c ) {
			var half,
				len = arry.length;
			if ( len > 1 ) {
				// https://gist.github.com/caseyjustus/1166258
				arry.sort( function( a, b ) { return a - b; } );
				half = Math.floor( len / 2 );
				return ( len % 2 ) ? arry[ half ] : ( arry[ half - 1 ] + arry[ half ] ) / 2;
			}
			return math.invalid( c, 'median', 1 );
		},
		mode : function( arry ) {
			// http://stackoverflow.com/a/3451640/145346
			var index, el, m,
				modeMap = {},
				maxCount = 1,
				modes = [ arry[ 0 ] ];
			for ( index = 0; index < arry.length; index++ ) {
				el = arry[ index ];
				modeMap[ el ] = modeMap[ el ] ? modeMap[ el ] + 1 : 1;
				m = modeMap[ el ];
				if ( m > maxCount ) {
					modes = [ el ];
					maxCount = m;
				} else if ( m === maxCount ) {
					modes[ modes.length ] = el;
					maxCount = m;
				}
			}
			// returns arry of modes if there is a tie
			return modes.sort( function( a, b ) { return a - b; } );
		},
		max : function(arry) {
			return Math.max.apply( Math, arry );
		},
		min : function(arry) {
			return Math.min.apply( Math, arry );
		},
		range: function(arry) {
			var v = arry.sort( function( a, b ) { return a - b; } );
			return v[ arry.length - 1 ] - v[ 0 ];
		},
		// common variance equation
		// (not accessible via data-attribute setting)
		variance: function( arry, population, c ) {
			var divisor,
				avg = ts.equations.mean( arry ),
				v = 0,
				i = arry.length;
			while ( i-- ) {
				v += Math.pow( ( arry[ i ] - avg ), 2 );
			}
			divisor = ( arry.length - ( population ? 0 : 1 ) );
			if ( divisor === 0 ) {
				return math.invalid( c, 'variance', 0 );
			}
			v /= divisor;
			return v;
		},
		// variance (population)
		varp : function( arry, c ) {
			return ts.equations.variance( arry, true, c );
		},
		// variance (sample)
		vars : function( arry, c ) {
			return ts.equations.variance( arry, false, c );
		},
		// standard deviation (sample)
		stdevs : function( arry, c ) {
			var vars = ts.equations.variance( arry, false, c );
			return Math.sqrt( vars );
		},
		// standard deviation (population)
		stdevp : function( arry, c ) {
			var varp = ts.equations.variance( arry, true, c );
			return Math.sqrt( varp );
		}
	};

	// add new widget called repeatHeaders
	// ************************************
	ts.addWidget({
		id: 'math',
		priority: 100,
		options: {
			math_data     : 'math',
			math_debug    : false,
			// column index to ignore
			math_ignore   : [],
			// mask info: https://code.google.com/p/javascript-number-formatter/
			math_mask     : '#,##0.00',
			// complete executed after each fucntion
			math_complete : null, // function($cell, wo, result, value, arry) { return result; },
			// math_completed called after all math calculations have completed
			math_completed: function( /* config */ ) {},
			// order of calculation; 'all' is last
			math_priority : [ 'row', 'above', 'below', 'col' ],
			// template for or just prepend the mask prefix & suffix with this HTML
			// e.g. '<span class="red">{content}</span>'
			math_prefix   : '',
			math_suffix   : '',
			// cell attribute containing the math value to use
			math_textAttr : '',
			// no matching math elements found (text added to cell)
			math_none     : 'N/A',
			math_event    : 'recalculate',
			// use this filter to target specific rows (e.g. ':visible', or ':not(.empty-row)')
			math_rowFilter: ''
		},
		init : function( table, thisWidget, c, wo ) {
			// filterEnd fires after updateComplete
			var update = ( ts.hasWidget( table, 'filter' ) ? 'filterEnd' : 'updateComplete' ) + '.tsmath';
			// filterEnd is when the pager hides rows... so bind to pagerComplete
			math.events += ( ts.hasWidget( table, 'pager' ) ? 'pagerComplete' : 'filterEnd' ) + '.tsmath ';
			c.$table
				.off( ( math.events + 'updateComplete.tsmath ' + wo.math_event ).replace( /\s+/g, ' ' ) )
				.on( math.events + wo.math_event, function( e ) {
					if ( !this.hasInitialized ) { return; }
					var init = e.type === 'tablesorter-initialized';
					if ( !wo.math_isUpdating || init ) {
						// don't setColumnIndexes on init here, or it gets done twice
						if ( !/filter/.test( e.type ) && !init ) {
							// redo data-column indexes on update
							math.setColumnIndexes( c );
						}
						math.recalculate( c, wo, init );
					}
				})
				.on( update, function() {
					setTimeout( function() {
						math.updateComplete( c );
					}, 40 );
				});
			wo.math_isUpdating = false;
			// math widget initialized after table - see #946
			if ( table.hasInitialized ) {
				math.recalculate( c, wo, true );
			}
		},
		// this remove function is called when using the refreshWidgets method or when destroying the tablesorter plugin
		// this function only applies to tablesorter v2.4+
		remove: function( table, c, wo, refreshing ) {
			if ( refreshing ) { return; }
			c.$table
				.off( ( math.events + ' updateComplete.tsmath ' + wo.math_event ).replace( /\s+/g, ' ' ) )
				.children().children( 'tr' ).children( '[data-' + wo.math_data + ']' ).empty();
		}
	});

})(jQuery);
