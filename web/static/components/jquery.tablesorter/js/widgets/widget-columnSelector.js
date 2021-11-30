/* Widget: columnSelector (responsive table widget) - updated 2018-08-03 (v2.31.2) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * by Justin Hallett & Rob Garrison
 */
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery: false */
;(function($) {
	'use strict';

	var ts = $.tablesorter,
	namespace = '.tscolsel',
	tsColSel = ts.columnSelector = {

		queryAll   : '@media only all { [columns] { display: none; } } ',
		queryBreak : '@media all and (min-width: [size]) { [columns] { display: table-cell; } } ',

		init: function(table, c, wo) {
			var $t, colSel,
				debug = ts.debug(c, 'columnSelector');

			// abort if no input is contained within the layout
			$t = $(wo.columnSelector_layout);
			if (!$t.find('input').add( $t.filter('input') ).length) {
				if (debug) {
					console.error('ColumnSelector >> ERROR: Column Selector aborting, no input found in the layout! ***');
				}
				return;
			}

			// unique table class name
			c.$table.addClass( c.namespace.slice(1) + 'columnselector' );

			// build column selector/state array
			colSel = c.selector = { $container : $(wo.columnSelector_container || '<div>') };
			colSel.$style = $('<style></style>').prop('disabled', true).appendTo('head');
			colSel.$breakpoints = $('<style></style>').prop('disabled', true).appendTo('head');

			colSel.isInitializing = true;
			tsColSel.setUpColspan(c, wo);
			tsColSel.setupSelector(c, wo);

			if (wo.columnSelector_mediaquery) {
				tsColSel.setupBreakpoints(c, wo);
			}

			colSel.isInitializing = false;
			if (colSel.$container.length) {
				tsColSel.updateCols(c, wo);
			} else if (debug) {
				console.warn('ColumnSelector >> container not found');
			}

			c.$table
				.off('refreshColumnSelector' + namespace)
				/* $('table').trigger('refreshColumnSelector', arguments ); showing arguments below
					undefined = refresh current settings (update css hiding columns)
					'selectors' = update container contents (replace inputs/labels)
					[ [2,3,4] ] = set visible columns; turn off "auto" mode.
					[ 'columns', [2,3,4] ] = set visible columns; turn off "auto" mode.
					[ 'auto', [2,3,4] ] = set visible columns; turn on "auto" mode.
					true = turn on "auto" mode.
				*/
				.on('refreshColumnSelector' + namespace, function( e, optName, optState ) {
					// make sure we're using current config settings
					tsColSel.refreshColumns( this.config, optName, optState );
				});

			if (debug) {
				console.log('ColumnSelector >> Widget initialized');
			}
		},

		refreshColumns: function( c, optName, optState ) {
			var i, arry, $el, val,
				colSel = c.selector,
				isArry = $.isArray(optState || optName),
				wo = c.widgetOptions;
			// see #798
			if (typeof optName !== 'undefined' && optName !== null && colSel.$container.length) {
				// pass "selectors" to update the all of the container contents
				if ( optName === 'selectors' ) {
					colSel.$container.empty();
					tsColSel.setupSelector(c, wo);
					tsColSel.setupBreakpoints(c, wo);
					// if optState is undefined, maintain the current "auto" state
					if ( typeof optState === 'undefined' && optState !== null ) {
						optState = colSel.auto;
					}
				}
				// pass an array of column zero-based indexes to turn off auto mode & toggle selected columns
				if (isArry) {
					arry = optState || optName;
					// make sure array contains numbers
					$.each(arry, function(i, v) {
						arry[i] = parseInt(v, 10);
					});
					for (i = 0; i < c.columns; i++) {
						val = $.inArray( i, arry ) >= 0;
						$el = colSel.$container.find( 'input[data-column=' + i + ']' );
						if ( $el.length ) {
							$el.prop( 'checked', val );
							colSel.states[i] = val;
						}
					}
				}
				// if passing an array, set auto to false to allow manual column selection & update columns
				// refreshColumns( c, 'auto', true ) === refreshColumns( c, true );
				val = optState === true || optName === true || optName === 'auto' && optState !== false;
				$el = colSel.$container.find( 'input[data-column="auto"]' ).prop( 'checked', val );
				tsColSel.updateAuto( c, wo, $el );
			} else {
				tsColSel.updateBreakpoints(c, wo);
				tsColSel.updateCols(c, wo);
			}
			tsColSel.saveValues( c, wo );
			tsColSel.adjustColspans( c, wo );
		},

		setupSelector: function(c, wo) {
			var index, name, $header, priority, col, colId, $el,
				colSel = c.selector,
				$container = colSel.$container,
				useStorage = wo.columnSelector_saveColumns && ts.storage,
				// get stored column states
				saved = useStorage ? ts.storage( c.table, 'tablesorter-columnSelector' ) : [],
				state = useStorage ? ts.storage( c.table, 'tablesorter-columnSelector-auto') : {};

			// initial states
			colSel.auto = $.isEmptyObject(state) || $.type(state.auto) !== 'boolean' ? wo.columnSelector_mediaqueryState : state.auto;
			colSel.states = [];
			colSel.$column = [];
			colSel.$wrapper = [];
			colSel.$checkbox = [];
			// populate the selector container
			for ( index = 0; index < c.columns; index++ ) {
				$header = c.$headerIndexed[ index ];
				// if no data-priority is assigned, default to 1, but don't remove it from the selector list
				priority = $header.attr(wo.columnSelector_priority) || 1;
				colId = $header.attr('data-column');
				col = ts.getColumnData( c.table, c.headers, colId );
				state = ts.getData( $header, col, 'columnSelector');

				// if this column not hidable at all
				// include getData check (includes 'columnSelector-false' class, data attribute, etc)
				if ( isNaN(priority) && priority.length > 0 || state === 'disable' ||
					( wo.columnSelector_columns[colId] && wo.columnSelector_columns[colId] === 'disable') ) {
					colSel.states[colId] = null;
					continue; // goto next
				}

				// set default state; storage takes priority
				colSel.states[colId] = saved && (typeof saved[colId] !== 'undefined' && saved[colId] !== null) ?
					saved[colId] : (typeof wo.columnSelector_columns[colId] !== 'undefined' && wo.columnSelector_columns[colId] !== null) ?
					wo.columnSelector_columns[colId] : (state === 'true' || state !== 'false');
				colSel.$column[colId] = $(this);
				if ($container.length) {
					// set default col title
					name = $header.attr(wo.columnSelector_name) || $header.text().trim();
					if (typeof wo.columnSelector_layoutCustomizer === 'function') {
						$el = $header.find('.' + ts.css.headerIn);
						name = wo.columnSelector_layoutCustomizer( $el.length ? $el : $header, name, parseInt(colId, 10) );
					}
					colSel.$wrapper[colId] = $(wo.columnSelector_layout.replace(/\{name\}/g, name)).appendTo($container);
					colSel.$checkbox[colId] = colSel.$wrapper[colId]
						// input may not be wrapped within the layout template
						.find('input').add( colSel.$wrapper[colId].filter('input') )
						.attr('data-column', colId)
						.toggleClass( wo.columnSelector_cssChecked, colSel.states[colId] )
						.prop('checked', colSel.states[colId])
						.on('change', function() {
							if (!colSel.isInitializing) {
								// ensure states is accurate
								var colId = $(this).attr('data-column');
								if (tsColSel.checkChange(c, this.checked)) {
									// if (wo.columnSelector_maxVisible)
									c.selector.states[colId] = this.checked;
									tsColSel.updateCols(c, wo);
								} else {
									this.checked = !this.checked;
									return false;
								}
							}
						}).change();
				}
			}

		},

		checkChange: function(c, checked) {
			var wo = c.widgetOptions,
				max = wo.columnSelector_maxVisible,
				min = wo.columnSelector_minVisible,
				states = c.selector.states,
				indx = states.length,
				count = 0;
			while (indx-- >= 0) {
				if (states[indx]) {
					count++;
				}
			}
			if ((checked & max !== null && count >= max) ||
				(!checked && min !== null && count <= min)) {
				return false;
			}
			return true;
		},

		setupBreakpoints: function(c, wo) {
			var colSel = c.selector;

			// add responsive breakpoints
			if (wo.columnSelector_mediaquery) {
				// used by window resize function
				colSel.lastIndex = -1;
				tsColSel.updateBreakpoints(c, wo);
				c.$table
					.off('updateAll' + namespace)
					.on('updateAll' + namespace, function() {
						tsColSel.setupSelector(c, wo);
						tsColSel.setupBreakpoints(c, wo);
						tsColSel.updateBreakpoints(c, wo);
						tsColSel.updateCols(c, wo);
					});
			}

			if (colSel.$container.length) {
				// Add media queries toggle
				if (wo.columnSelector_mediaquery) {
					colSel.$auto = $( wo.columnSelector_layout.replace(/\{name\}/g, wo.columnSelector_mediaqueryName) ).prependTo(colSel.$container);
					colSel.$auto
						// needed in case the input in the layout is not wrapped
						.find('input').add( colSel.$auto.filter('input') )
						.attr('data-column', 'auto')
						.prop('checked', colSel.auto)
						.toggleClass( wo.columnSelector_cssChecked, colSel.auto )
						.on('change', function() {
							tsColSel.updateAuto(c, wo, $(this));
						}).change();
				}
				// Add a bind on update to re-run col setup
				c.$table.off('update' + namespace).on('update' + namespace, function() {
					tsColSel.updateCols(c, wo);
				});
			}
		},

		updateAuto: function(c, wo, $el) {
			var colSel = c.selector;
			colSel.auto = $el.prop('checked') || false;
			$.each( colSel.$checkbox, function(i, $cb) {
				if ($cb) {
					$cb[0].disabled = colSel.auto;
					colSel.$wrapper[i].toggleClass('disabled', colSel.auto);
				}
			});
			if (wo.columnSelector_mediaquery) {
				tsColSel.updateBreakpoints(c, wo);
			}
			tsColSel.updateCols(c, wo);
			// copy the column selector to a popup/tooltip
			if (c.selector.$popup) {
				c.selector.$popup.find('.tablesorter-column-selector')
					.html( colSel.$container.html() )
					.find('input').each(function() {
						var indx = $(this).attr('data-column');
						$(this).prop( 'checked', indx === 'auto' ? colSel.auto : colSel.states[indx] );
					});
			}
			tsColSel.saveValues( c, wo );
			tsColSel.adjustColspans( c, wo );
			// trigger columnUpdate if auto is true (it gets skipped in updateCols()
			if (colSel.auto) {
				c.$table.triggerHandler(wo.columnSelector_updated);
			}
		},
		addSelectors: function( wo, prefix, column ) {
			var array = [],
				temp = ' col:nth-child(' + column + ')';
			array.push(prefix + temp + ',' + prefix + '_extra_table' + temp);
			temp = ' tr:not(.' + wo.columnSelector_classHasSpan + ') th[data-column="' + ( column - 1 ) + '"]';
			array.push(prefix + temp + ',' + prefix + '_extra_table' + temp);
			temp = ' tr:not(.' + wo.columnSelector_classHasSpan + ') td:nth-child(' + column + ')';
			array.push(prefix + temp + ',' + prefix + '_extra_table' + temp);
			// for other cells in colspan columns
			temp = ' tr td:not(' + prefix + wo.columnSelector_classHasSpan + ')[data-column="' + (column - 1) + '"]';
			array.push(prefix + temp + ',' + prefix + '_extra_table' + temp);
			return array;
		},
		updateBreakpoints: function(c, wo) {
			var priority, col, column, breaks,
				isHidden = [],
				colSel = c.selector,
				prefix = c.namespace + 'columnselector',
				mediaAll = [],
				breakpts = '';
			if (wo.columnSelector_mediaquery && !colSel.auto) {
				colSel.$breakpoints.prop('disabled', true);
				colSel.$style.prop('disabled', false);
				return;
			}
			if (wo.columnSelector_mediaqueryHidden) {
				// add columns to be hidden; even when "auto" is set - see #964
				for ( column = 0; column < c.columns; column++ ) {
					col = ts.getColumnData( c.table, c.headers, column );
					isHidden[ column + 1 ] = ts.getData( c.$headerIndexed[ column ], col, 'columnSelector' ) === 'false';
					if ( isHidden[ column + 1 ] ) {
						// hide columnSelector false column (in auto mode)
						mediaAll = mediaAll.concat( tsColSel.addSelectors( wo, prefix, column + 1 ) );
					}
				}
			}
			// only 6 breakpoints (same as jQuery Mobile)
			for (priority = 0; priority < wo.columnSelector_maxPriorities; priority++) {
				/*jshint loopfunc:true */
				breaks = [];
				c.$headers.filter('[' + wo.columnSelector_priority + '=' + (priority + 1) + ']').each(function() {
					column = parseInt($(this).attr('data-column'), 10) + 1;
					// don't reveal columnSelector false columns
					if ( !isHidden[ column ] ) {
						breaks = breaks.concat( tsColSel.addSelectors( wo, prefix, column ) );
					}
				});
				if (breaks.length) {
					mediaAll = mediaAll.concat( breaks );
					breakpts += tsColSel.queryBreak
						.replace(/\[size\]/g, wo.columnSelector_breakpoints[priority])
						.replace(/\[columns\]/g, breaks.join(','));
				}
			}
			if (colSel.$style) {
				colSel.$style.prop('disabled', true);
			}
			if (mediaAll.length) {
				colSel.$breakpoints
					.prop('disabled', false)
					.text( tsColSel.queryAll.replace(/\[columns\]/g, mediaAll.join(',')) + breakpts );
			}
		},
		updateCols: function(c, wo) {
			if (wo.columnSelector_mediaquery && c.selector.auto || c.selector.isInitializing) {
				return;
			}
			var column,
				colSel = c.selector,
				styles = [],
				prefix = c.namespace + 'columnselector';
			colSel.$container.find('input[data-column]').filter('[data-column!="auto"]').each(function() {
				if (!this.checked) {
					column = parseInt( $(this).attr('data-column'), 10 ) + 1;
					styles = styles.concat( tsColSel.addSelectors( wo, prefix, column ) );
				}
				$(this).toggleClass( wo.columnSelector_cssChecked, this.checked );
			});
			if (wo.columnSelector_mediaquery) {
				colSel.$breakpoints.prop('disabled', true);
			}
			if (colSel.$style) {
				colSel.$style.prop('disabled', false).text( styles.length ? styles.join(',') + ' { display: none; }' : '' );
			}
			tsColSel.saveValues( c, wo );
			tsColSel.adjustColspans( c, wo );
			c.$table.triggerHandler(wo.columnSelector_updated);
		},

		setUpColspan: function(c, wo) {
			var index, span, nspace,
				$window = $( window ),
				hasSpans = false,
				$cells = c.$table
					.add( $(c.namespace + '_extra_table') )
					.children()
					.children('tr')
					.children('th, td'),
				len = $cells.length;
			for ( index = 0; index < len; index++ ) {
				span = $cells[ index ].colSpan;
				if ( span > 1 ) {
					hasSpans = true;
					$cells.eq( index )
						.addClass( c.namespace.slice( 1 ) + 'columnselector' + wo.columnSelector_classHasSpan )
						.attr( 'data-col-span', span );
					// add data-column values
					ts.computeColumnIndex( $cells.eq( index ).parent().addClass( wo.columnSelector_classHasSpan ) );
				}
			}
			// only add resize end if using media queries
			if ( hasSpans && wo.columnSelector_mediaquery ) {
				nspace = c.namespace + 'columnselector';
				// Setup window.resizeEnd event
				$window
					.off( nspace )
					.on( 'resize' + nspace, ts.window_resize )
					.on( 'resizeEnd' + nspace, function() {
						// IE calls resize when you modify content, so we have to unbind the resize event
						// so we don't end up with an infinite loop. we can rebind after we're done.
						$window.off( 'resize' + nspace, ts.window_resize );
						tsColSel.adjustColspans( c, wo );
						$window.on( 'resize' + nspace, ts.window_resize );
					});
			}
		},

		// Extracted from buildHeaders in core; needed for scroller widget compatibility
		findHeaders : function(c) {
			var indx, $temp,
				sel = '.' + ts.css.scrollerHeader + ' thead > tr > ',
				$headers = $(sel + 'th,' + sel + 'td'),
				result = [];
			for ( indx = 0; indx < c.columns; indx++ ) {
				// Use $headers.parent() in case selectorHeaders doesn't point to the th/td
				$temp = $headers.filter( '[data-column="' + indx + '"]' );
				// target sortable column cells, unless there are none, then use non-sortable cells
				// .last() added in jQuery 1.4; use .filter(':last') to maintain compatibility with jQuery v1.2.6
				result[ indx ] = $temp.length ?
					$temp.not( '.sorter-false' ).length ?
						$temp.not( '.sorter-false' ).filter( ':last' ) :
						$temp.filter( ':last' ) :
					$();
			}
			return result;
		},

		adjustColspans: function(c, wo) {
			var index, cols, col, span, end, $cell,
				colSel = c.selector,
				filtered = wo.filter_filteredRow || 'filtered',
				autoModeOn = wo.columnSelector_mediaquery && colSel.auto,
				// find all header/footer cells in case a regular column follows a colspan; see #1238
				$headers = c.$table.children( 'thead, tfoot' ).children().children()
					.add( $(c.namespace + '_extra_table').children( 'thead, tfoot' ).children().children() )
					// include grouping widget headers (they have colspans!)
					.add( c.$table.find( '.group-header' ).children() ),
				len = $headers.length,
				$headerIndexed = ts.hasWidget(c.table, 'scroller')
					? tsColSel.findHeaders(c)
					: c.$headerIndexed;
			for ( index = 0; index < len; index++ ) {
				$cell = $headers.eq(index);
				col = parseInt( $cell.attr('data-column'), 10 ) || $cell[0].cellIndex;
				span = parseInt( $cell.attr('data-col-span'), 10 ) || 1;
				end = col + span;
				if ( span > 1 ) {
					for ( cols = col; cols < end; cols++ ) {
						if ( !autoModeOn && colSel.states[ cols ] === false ||
							autoModeOn && $headerIndexed[ cols ] && !$headerIndexed[ cols ].is(':visible') ) {
							span--;
						}
					}
					if ( span ) {
						$cell.removeClass( filtered )[0].colSpan = span;
					} else {
						$cell.addClass( filtered );
					}
				} else if ( typeof colSel.states[ col ] !== 'undefined' && colSel.states[ col ] !== null ) {
					$cell.toggleClass( filtered, !autoModeOn && !colSel.states[ col ] );
				}
			}
		},

		saveValues : function( c, wo ) {
			if ( wo.columnSelector_saveColumns && ts.storage ) {
				var colSel = c.selector;
				ts.storage( c.$table[0], 'tablesorter-columnSelector-auto', { auto : colSel.auto } );
				ts.storage( c.$table[0], 'tablesorter-columnSelector', colSel.states );
			}
		},

		attachTo : function(table, elm) {
			table = $(table)[0];
			var colSel, wo, indx,
				c = table.config,
				$popup = $(elm);
			if ($popup.length && c) {
				if (!$popup.find('.tablesorter-column-selector').length) {
					// add a wrapper to add the selector into, in case the popup has other content
					$popup.append('<span class="tablesorter-column-selector"></span>');
				}
				colSel = c.selector;
				wo = c.widgetOptions;
				$popup.find('.tablesorter-column-selector')
					.html( colSel.$container.html() )
					.find('input').each(function() {
						var indx = $(this).attr('data-column'),
							isChecked = indx === 'auto' ? colSel.auto : colSel.states[indx];
						$(this)
							.toggleClass( wo.columnSelector_cssChecked, isChecked )
							.prop( 'checked', isChecked );
					});
				colSel.$popup = $popup.on('change', 'input', function() {
					if (!colSel.isInitializing) {
						if (tsColSel.checkChange(c, this.checked)) {
							// data input
							indx = $(this).toggleClass( wo.columnSelector_cssChecked, this.checked ).attr('data-column');
							// update original popup
							colSel.$container.find('input[data-column="' + indx + '"]')
								.prop('checked', this.checked)
								.trigger('change');
						} else {
							this.checked = !this.checked;
							return false;
						}
					}
				});
			}
		}

	};

	/* Add window resizeEnd event (also used by scroller widget) */
	ts.window_resize = function() {
		if ( ts.timer_resize ) {
			clearTimeout( ts.timer_resize );
		}
		ts.timer_resize = setTimeout( function() {
			$( window ).trigger( 'resizeEnd' );
		}, 250 );
	};

	ts.addWidget({
		id: 'columnSelector',
		priority: 10,
		options: {
			// target the column selector markup
			columnSelector_container : null,
			// column status, true = display, false = hide
			// disable = do not display on list
			columnSelector_columns : {},
			// remember selected columns
			columnSelector_saveColumns: true,

			// container layout
			columnSelector_layout : '<label><input type="checkbox">{name}</label>',
			// layout customizer callback called for each column
			// function($cell, name, column) { return name || $cell.html(); }
			columnSelector_layoutCustomizer : null,
			// data attribute containing column name to use in the selector container
			columnSelector_name : 'data-selector-name',

			/* Responsive Media Query settings */
			// enable/disable mediaquery breakpoints
			columnSelector_mediaquery : true,
			// toggle checkbox name
			columnSelector_mediaqueryName : 'Auto: ',
			// breakpoints checkbox initial setting
			columnSelector_mediaqueryState : true,
			// hide columnSelector false columns while in auto mode
			columnSelector_mediaqueryHidden : false,
			// set the maximum and/or minimum number of visible columns
			columnSelector_maxVisible : null,
			columnSelector_minVisible : null,

			// responsive table hides columns with priority 1-6 at these breakpoints
			// see http://view.jquerymobile.com/1.3.2/dist/demos/widgets/table-column-toggle/#Applyingapresetbreakpoint
			// *** set to false to disable ***
			columnSelector_breakpoints : [ '20em', '30em', '40em', '50em', '60em', '70em' ],
			// maximum number of priority settings; if this value is changed (especially increased),
			// then make sure to modify the columnSelector_breakpoints - see #1204
			columnSelector_maxPriorities : 6,
			// data attribute containing column priority
			// duplicates how jQuery mobile uses priorities:
			// http://view.jquerymobile.com/1.3.2/dist/demos/widgets/table-column-toggle/
			columnSelector_priority : 'data-priority',
			// class name added to checked checkboxes - this fixes an issue with Chrome not updating FontAwesome
			// applied icons; use this class name (input.checked) instead of input:checked
			columnSelector_cssChecked : 'checked',
			// class name added to rows that have a span (e.g. grouping widget & other rows inside the tbody)
			columnSelector_classHasSpan : 'hasSpan',
			// event triggered when columnSelector completes
			columnSelector_updated : 'columnUpdate'
		},
		init: function(table, thisWidget, c, wo) {
			tsColSel.init(table, c, wo);
		},
		remove: function(table, c, wo, refreshing) {
			var csel = c.selector;
			if ( refreshing || !csel ) { return; }
			if ( csel ) { csel.$container.empty(); }
			if ( csel.$popup ) { csel.$popup.empty(); }
			csel.$style.remove();
			csel.$breakpoints.remove();
			$( c.namespace + 'columnselector' + wo.columnSelector_classHasSpan )
				.removeClass( wo.filter_filteredRow || 'filtered' );
			c.$table.find('[data-col-span]').each(function(indx, el) {
				var $el = $(el);
				$el.attr('colspan', $el.attr('data-col-span'));
			});
			c.$table.off('updateAll' + namespace + ' update' + namespace);
		}

	});

})(jQuery);
