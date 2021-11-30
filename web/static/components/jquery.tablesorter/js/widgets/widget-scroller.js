/*! Widget: scroller - updated 2018-05-07 (v2.30.4) *//*
	Copyright (C) 2011 T. Connell & Associates, Inc.

	Dual-licensed under the MIT and GPL licenses

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
	LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
	NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE	FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
	WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
	SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

	Resizable scroller widget for the jQuery tablesorter plugin

	Version 2.0 - modified by Rob Garrison 4/12/2013;
	updated 3/5/2015 (v2.22.2) with lots of help from TheSin-
	Requires jQuery v1.7+
	Requires the tablesorter plugin, v2.8+, available at http://mottie.github.com/tablesorter/docs/

	Usage:
		$(function() {
			$('table.tablesorter').tablesorter({
				widgets: ['zebra', 'scroller'],
				widgetOptions : {
					scroller_height       : 300,  // height of scroll window
					scroller_jumpToHeader : true, // header snap to browser top when scrolling the tbody
					scroller_upAfterSort  : true, // scroll tbody to top after sorting
					scroller_fixedColumns : 0     // set number of fixed columns
				}
			});
		});

	Website: www.tconnell.com
*/
/*jshint browser:true, jquery:true, unused:false */
;( function( $, window ) {
	'use strict';

	var ts = $.tablesorter,
		tscss = ts.css;

	$.extend( ts.css, {
		scrollerWrap        : 'tablesorter-scroller',
		scrollerHeader      : 'tablesorter-scroller-header',
		scrollerTable       : 'tablesorter-scroller-table',
		scrollerFooter      : 'tablesorter-scroller-footer',
		scrollerFixed       : 'tablesorter-scroller-fixed',
		scrollerFixedPanel  : 'tablesorter-scroller-fixed-panel',
		scrollerHasFix      : 'tablesorter-scroller-has-fixed-columns',
		scrollerHideColumn  : 'tablesorter-scroller-hidden-column',
		scrollerHideElement : 'tablesorter-scroller-hidden',
		scrollerSpacerRow   : 'tablesorter-scroller-spacer',
		scrollerBarSpacer   : 'tablesorter-scroller-bar-spacer',
		scrollerAddedHeight : 'tablesorter-scroller-added-height',
		scrollerHack        : 'tablesorter-scroller-scrollbar-hack',
		// class name on table cannot start with 'tablesorter-' or the
		// suffix 'scroller-rtl' will match as a theme name
		scrollerRtl         : 'ts-scroller-rtl'
	});

	ts.addWidget({
		id : 'scroller',
		priority : 60, // run after the filter widget
		options : {
			scroller_height : 300,
			// pop table header into view while scrolling up the page
			scroller_jumpToHeader : true,
			// scroll tbody to top after sorting
			scroller_upAfterSort : true,
			// set number of fixed columns
			scroller_fixedColumns : 0,
			// add hover highlighting to the fixed column (disable if it causes slowing)
			scroller_rowHighlight : 'hover',
			// add a fixed column overlay for styling
			scroller_addFixedOverlay : false,
			// In tablesorter v2.19.0 the scroll bar width is auto-detected
			// add a value here to override the auto-detected setting
			scroller_barWidth : null
		},
		format : function( table, c, wo ) {
			if ( c.isScrolling ) {
				ts.scroller.resize( c, wo );
			} else {
				// initialize here instead of in widget init to give the
				// filter widget time to finish building the filter row
				ts.scroller.setup( c, wo );
			}
		},
		remove : function( table, c, wo ) {
			ts.scroller.remove( c, wo );
		}
	});

	/* Add window resizeEnd event (also used by columnSelector widget) */
	ts.window_resize = function() {
		if ( ts.timer_resize ) {
			clearTimeout( ts.timer_resize );
		}
		ts.timer_resize = setTimeout( function() {
			$( window ).trigger( 'resizeEnd' );
		}, 250 );
	};

	// Add extra scroller css
	$( function() {
		var style = '<style>' +
			/* overall wrapper & table section wrappers */
			'.' + tscss.scrollerWrap + ' { position: relative; overflow: hidden; }' +
			/* add border-box sizing to all scroller widget tables; see #135 */
			'.' + tscss.scrollerWrap + ' * { box-sizing: border-box; }' +
			'.' + tscss.scrollerHeader + ', .' + tscss.scrollerFooter + ' { position: relative; overflow: hidden; }' +
			'.' + tscss.scrollerHeader + ' table.' + tscss.table + ' { margin-bottom: 0; }' +
			/* always leave the scroll bar visible for tbody, or table overflows into the scrollbar
			when height < max height (filtering) */
			'.' + tscss.scrollerTable + ' { position: relative; overflow: auto; }' +
			'.' + tscss.scrollerTable + ' table.' + tscss.table +
				' { border-top: 0; margin-top: 0; margin-bottom: 0; overflow: hidden; max-width: initial; }' +
			/* hide footer in original table */
			'.' + tscss.scrollerTable + ' tfoot, .' + tscss.scrollerHideElement + ', .' + tscss.scrollerHideColumn +
				' { display: none; }' +

			/*** fixed column ***/
			/* disable pointer-events on fixed column wrapper or the user can't interact with the horizontal scrollbar */
			'.' + tscss.scrollerFixed + ', .' + tscss.scrollerFixed + ' .' + tscss.scrollerFixedPanel +
				' { pointer-events: none; }' +
			/* enable pointer-events for fixed column children; see #135 & #878 */
			'.' + tscss.scrollerFixed + ' > div { pointer-events: all; }' +
			'.' + tscss.scrollerWrap + ' .' + tscss.scrollerFixed + ' { position: absolute; top: 0; z-index: 1; left: 0 } ' +
			'.' + tscss.scrollerWrap + ' .' + tscss.scrollerFixed + '.' + tscss.scrollerRtl + ' { left: auto; right: 0 } ' +
			/* add horizontal scroll bar; set to 'auto', see #135 */
			'.' + tscss.scrollerWrap + '.' + tscss.scrollerHasFix + ' > .' + tscss.scrollerTable + ' { overflow: auto; }' +
			/* need to position the tbody & tfoot absolutely to hide the scrollbar & move the footer
			below the horizontal scrollbar */
			'.' + tscss.scrollerFixed + ' .' + tscss.scrollerFooter + ' { position: absolute; bottom: 0; }' +
			/* hide fixed tbody scrollbar - see http://goo.gl/VsLe6n - set overflow to auto here for mousewheel scroll */
			'.' + tscss.scrollerFixed + ' .' + tscss.scrollerTable +
				' { position: relative; left: 0; overflow: auto; -ms-overflow-style: none; }' +
			'.' + tscss.scrollerFixed + ' .' + tscss.scrollerTable + '::-webkit-scrollbar { display: none; }' +
			/*** fixed column panel ***/
			'.' + tscss.scrollerWrap + ' .' + tscss.scrollerFixedPanel +
				' { position: absolute; top: 0; bottom: 0; z-index: 2; left: 0; right: 0; } ' +
			'</style>';
		$( 'head' ).append( style );
	});

	ts.scroller = {

		// Ugh.. Firefox misbehaves, so it needs to be detected
		isFirefox : navigator.userAgent.toLowerCase().indexOf( 'firefox' ) > -1,
		// old IE needs a wrap to hide the fixed column scrollbar; http://stackoverflow.com/a/24408672/145346
		isOldIE : document.all && !window.atob,
		isIE : ( document.all && !window.atob ) || navigator.appVersion.indexOf( 'Trident/' ) > 0,
		// http://stackoverflow.com/questions/7944460/detect-safari-browser - needed to position scrolling body
		// when the table is set up in RTL direction
		isSafari : navigator.userAgent.toLowerCase().indexOf( 'safari' ) > -1 &&
			navigator.userAgent.toLowerCase().indexOf( 'chrome' ) === -1,

		hasScrollBar : function( $target, checkWidth ) {
			if ( checkWidth ) {
				return $target.get(0).scrollWidth > $target.width();
			} else {
				return $target.get(0).scrollHeight > $target.height();
			}
		},

		setWidth : function( $el, width ) {
			$el.css({
				'width' : width,
				'min-width' : width,
				'max-width' : width
			});
		},

		// modified from http://davidwalsh.name/detect-scrollbar-width
		getBarWidth : function() {
			var $div = $( '<div>' ).css({
				'position' : 'absolute',
				'top' : '-9999px',
				'left' : 0,
				'width' : '100px',
				'height' : '100px',
				'overflow' : 'scroll',
				'visibility' : 'hidden'
			}).appendTo( 'body' ),
			div = $div[0],
			barWidth = div.offsetWidth - div.clientWidth;
			$div.remove();
			return barWidth;
		},

		setup : function( c, wo ) {
			var tbHt, $hdr, $t, $hCells, $tableWrap, events, tmp, detectedWidth,
				$win = $( window ),
				tsScroller = ts.scroller,
				namespace = c.namespace + 'tsscroller',
				$foot = $(),
				// c.namespace contains a unique tablesorter ID, per table
				id = c.namespace.slice( 1 ) + 'tsscroller',
				$table = c.$table;

			// force config.widthFixed option - this helps maintain proper alignment across cloned tables
			c.widthFixed = true;

			wo.scroller_calcWidths = [];
			wo.scroller_saved = [ 0, 0 ];
			wo.scroller_isBusy = true;
			wo.scroller_scrollTimer = null;

			// set scrollbar width to one of the following (1) explicitly set scroller_barWidth option,
			// (2) detected scrollbar width or (3) fallback of 15px
			if ( wo.scroller_barWidth !== null ) {
				wo.scroller_barSetWidth = wo.scroller_barWidth;
			} else {
				detectedWidth = tsScroller.getBarWidth();
				wo.scroller_barSetWidth = detectedWidth !== null ? detectedWidth : 15;
			}

			tmp = $table.children( 'caption' );

			$hdr = $( '<table class="' + $table.attr( 'class' ) + '" cellpadding=0 cellspacing=0>' +
				( tmp.length ? tmp[ 0 ].outerHTML : '' ) +
				$table.children( 'thead' )[ 0 ].outerHTML + '</table>' );
			wo.scroller_$header = $hdr.addClass( c.namespace.slice( 1 ) + '_extra_table' );

			$t = $table.children( 'tfoot' );
			if ( $t.length ) {
				$foot = $( '<table class="' + $table.attr( 'class' ) +
					'" cellpadding=0 cellspacing=0 style="margin-top:0"></table>' )
					.addClass( c.namespace.slice( 1 ) + '_extra_table' )
					// maintain any bindings on the tfoot cells
					.append( $t.clone( true ) )
					.wrap( '<div class="' + tscss.scrollerFooter + '"/>' );
			}
			wo.scroller_$footer = $foot;

			$table
				.wrap( '<div id="' + id + '" class="' + tscss.scrollerWrap + '" />' )
				.before( $hdr )
				// shrink filter row but don't completely hide it because the inputs/selectors may distort the columns
				.find( '.' + tscss.filterRow )
				.addClass( tscss.filterRowHide );

			wo.scroller_$container = $table.parent();

			if ( $foot.length ) {
				// $foot.parent() to include <div> wrapper
				$table.after( $foot.parent() );
			}

			$hCells = $hdr
				.wrap( '<div class="' + tscss.scrollerHeader + '" />' )
				.find( '.' + tscss.header );

			// if max-height is greater than 0 use max-height, so the height resizes dynamically while filtering
			// else let the table not have a vertical scroll
			$table.wrap( '<div class="' + tscss.scrollerTable +
				( wo.scroller_height > 0 ? '" style="max-height:' + wo.scroller_height + 'px;">' : '">' ) );
			$tableWrap = $table.parent();

			// make scroller header sortable
			ts.bindEvents( c.table, $hCells );

			// look for filter widget
			if ( $table.hasClass( 'hasFilters' ) ) {
				ts.filter.bindSearch( $table, $hdr.find( '.' + tscss.filter ) );
			}

			$table
				.children( 'thead, caption' )
				.addClass( tscss.scrollerHideElement );
			tbHt = $tableWrap.parent().height();

			// The header will always jump into view if scrolling the table body
			$tableWrap
				.off( 'scroll' + namespace )
				.on( 'scroll' + namespace, function() {
					// Save position
					clearTimeout(wo.scroller_scrollTimer);
					wo.scroller_scrollTimer = setTimeout(function() {
						wo.scroller_saved[0] = $tableWrap.scrollLeft();
						wo.scroller_saved[1] = $tableWrap.scrollTop();
					}, 300);
					if ( wo.scroller_jumpToHeader ) {
						var pos = $win.scrollTop() - $hdr.offset().top;
						if ( $( this ).scrollTop() !== 0 && pos < tbHt && pos > 0 ) {
							$win.scrollTop( $hdr.offset().top );
						}
					}
					$hdr
						.parent()
						.add( $foot.parent() )
						.scrollLeft( $( this ).scrollLeft() );
				});

			// resize/update events - filterEnd fires after "tablesorter-initialized" and "updateComplete"
			tmp = ts.hasWidget( c.table, 'filter' ) ?
				'filterEnd filterInit' :
				'tablesorter-initialized updateComplete';
			events = ( tmp + ' sortEnd pagerComplete columnUpdate ' ).split( ' ' ).join( namespace + ' ' );

			$table
				.off( namespace )
				.on( 'sortStart' + namespace, function() {
					clearTimeout(wo.scroller_scrollTimer);
					wo.scroller_isBusy = true;
				})
				.on( 'sortEnd filterEnd'.split( ' ' ).join( namespace + ' ' ), function( event ) {
					// Sorting, so scroll to top
					if ( event.type === 'sortEnd' && wo.scroller_upAfterSort ) {
						$tableWrap
							.scrollLeft( wo.scroller_saved[0] )
							.animate({ scrollTop : 0 }, 'fast', function() {
								wo.scroller_isBusy = false;
							});
					} else if ( wo.scroller_fixedColumns ) {
						setTimeout( function() {
							// restore previous scroll position
							$tableWrap
								.scrollTop( wo.scroller_saved[1] )
								.scrollLeft( wo.scroller_saved[0] );
							tsScroller.updateFixed( c, wo );
						}, 0 );
					}
				})
				.on( 'setFixedColumnSize' + namespace, function( event, size ) {
					var $wrap = wo.scroller_$container;
					if ( typeof size !== 'undefined' && !isNaN( size ) ) {
						wo.scroller_fixedColumns = parseInt( size, 10 );
					}
					// remove fixed columns
					tsScroller.removeFixed( c, wo );
					size = wo.scroller_fixedColumns;
					if ( size > 0 && size < c.columns - 1 ) {
						tsScroller.updateFixed( c, wo );
					} else if ( $wrap.hasClass( tscss.scrollerHasFix ) ) {
						$wrap.removeClass( tscss.scrollerHasFix );
						// resize needed to make tables full width
						tsScroller.resize( c, wo );
					}
				})
				.on( events, function( event ) {
					// Stop from running twice with pager
					if ( ts.hasWidget( 'pager' ) && event.type === 'updateComplete' ) {
						return;
					}
					if ( wo.scroller_fixedColumns > 0 ) {
						tsScroller.updateFixed( c, wo );
					}
					// adjust column sizes after an update
					tsScroller.resize( c, wo );
				});

			// Setup window.resizeEnd event
			$win
				.off( 'resize resizeEnd '.split( ' ' ).join( namespace + ' ' ) )
				.on( 'resize' + namespace, ts.window_resize )
				.on( 'resizeEnd' + namespace, function() {
					// IE calls resize when you modify content, so we have to unbind the resize event
					// so we don't end up with an infinite loop. we can rebind after we're done.
					$win.off( 'resize' + namespace, ts.window_resize );
					tsScroller.resize( c, wo );
					$win.on( 'resize' + namespace, ts.window_resize );
					$tableWrap.trigger( 'scroll' + namespace );
				});

			// initialization flag
			c.isScrolling = true;

			tsScroller.updateFixed( c, wo );

			// updateAll called - need to give the browser time to adjust the layout
			// before calculating fix column widths
			if ( c.table.hasInitialized && c.isScrolling ) {
				setTimeout(function() {
					ts.scroller.resize( c, wo );
				}, 50);
			}

		},

		resize : function( c, wo ) {
			if ( wo.scroller_isBusy ) { return; }
			var index, borderWidth, setWidth, $headers, $this,
				tsScroller = ts.scroller,
				$container = wo.scroller_$container,
				$table = c.$table,
				$tableWrap = $table.parent(),
				$hdr = wo.scroller_$header,
				$foot = wo.scroller_$footer,
				$win = $(window),
				position = [ $win.scrollLeft(), $win.scrollTop() ],
				id = c.namespace.slice( 1 ) + 'tsscroller',
				// Hide other scrollers so we can resize
				$div = $( 'div.' + tscss.scrollerWrap + '[id!="' + id + '"]' )
					.addClass( tscss.scrollerHideElement ),
				temp = 'padding:0;margin:0;border:0;height:0;max-height:0;min-height:0;',
				row = '<tr class="' + tscss.scrollerSpacerRow + ' ' + c.selectorRemove.slice(1) +
					'" style="' + temp + '">';

			wo.scroller_calcWidths = [];

			// Remove fixed so we get proper widths and heights
			tsScroller.removeFixed( c, wo );
			$container.find( '.' + tscss.scrollerSpacerRow ).remove();
			// remove ts added colgroups
			$container.find( '.' + ts.css.colgroup ).remove();

			// show original table elements to get proper alignment
			$table
				.find( '.' + tscss.scrollerHideElement )
				.removeClass( tscss.scrollerHideElement );

			// include left & right border widths
			borderWidth = parseInt( $table.css( 'border-left-width' ), 10 );

			$headers = c.$headerIndexed;

			for ( index = 0; index < c.columns; index++ ) {
				$this = $headers[ index ];
				// code from https://github.com/jmosbech/StickyTableHeaders
				if ( $this.css( 'box-sizing' ) === 'border-box' ) {
					setWidth = $this.outerWidth();
				} else {
					if ( $this.css( 'border-collapse' ) === 'collapse' ) {
						if ( $this.length && window.getComputedStyle ) {
							setWidth = parseFloat( window.getComputedStyle( $this[ 0 ], null ).width );
						} else {
							// ie8 only
							setWidth = $this.outerWidth() - parseFloat( $this.css( 'padding-left' ) ) -
								parseFloat( $this.css( 'padding-right' ) ) -
								( parseFloat( $this.css( 'border-width' ) ) || 0 );
						}
					} else {
						setWidth = $this.width();
					}
				}
				row += '<td data-column="' + index + '" style="' + temp + 'width:' + setWidth +
					'px;min-width:' + setWidth + 'px;max-width:' + setWidth + 'px"></td>';

				// save current widths
				wo.scroller_calcWidths[ index ] = setWidth;
			}
			row += '</tr>';
			c.$tbodies.eq(0).append( row ); // tbody
			$hdr.children( 'thead' ).append( row );
			$foot.children( 'tfoot' ).append( row );

			// include colgroup or alignment is off
			ts.fixColumnWidth( c.table );
			row = c.$table.children( 'colgroup' )[0].outerHTML;
			$hdr.append( row );
			$foot.append( row );

			temp = $tableWrap.parent().innerWidth() -
				( tsScroller.hasScrollBar( $tableWrap ) ? wo.scroller_barSetWidth : 0 );
			$tableWrap.width( temp );

			temp = ( tsScroller.hasScrollBar( $tableWrap ) ? wo.scroller_barSetWidth : 0 ) + borderWidth;
			setWidth = $tableWrap.innerWidth() - temp;

			$hdr
				.parent()
				.add( $foot.parent() )
				.width( setWidth );

			$tableWrap
				.width( setWidth + temp );

			// hide original table thead
			$table.children( 'thead, caption' ).addClass( tscss.scrollerHideElement );

			// update fixed column sizes
			tsScroller.updateFixed( c, wo );

			$div.removeClass( tscss.scrollerHideElement );

			// restore scrollTop - fixes #926
			$tableWrap.scrollTop( wo.scroller_saved[1] );
			wo.scroller_$container
				.find( '.' + tscss.scrollerFixed )
				.find( '.' + tscss.scrollerTable )
				.scrollTop( wo.scroller_saved[1] );
			$win.scrollLeft( position[0] );
			$win.scrollTop( position[1] );

			// update resizable widget handles
			setTimeout( function() {
				c.$table.triggerHandler( 'resizableUpdate' );
				c.$table.triggerHandler( 'scrollerComplete' );
			}, 100 );

		},

		// Add fixed (frozen) columns (Do not call directly, use updateFixed)
		setupFixed : function( c, wo ) {
			var index, index2, $el, len, temp, $fixedColumn, $fixedTbody,
				$table = c.$table,
				$wrapper = wo.scroller_$container,
				fixedColumns = wo.scroller_fixedColumns;

			$fixedColumn = $wrapper
				.addClass( tscss.scrollerHasFix )
				.clone()
				.addClass( tscss.scrollerFixed )
				.removeClass( tscss.scrollerWrap )
				.attr( 'id', '' );

			$fixedColumn.find('caption').html('&nbsp;');

			if ( wo.scroller_addFixedOverlay ) {
				$fixedColumn.append( '<div class="' + tscss.scrollerFixedPanel + '">' );
			}

			$fixedTbody = $fixedColumn.find( '.' + tscss.scrollerTable );
			$fixedTbody
				.children( 'table' )
				.addClass( c.namespace.slice( 1 ) + '_extra_table' )
				.attr( 'id', '' )
				.children( 'thead, tfoot' )
				.remove();

			wo.scroller_$fixedColumns = $fixedColumn;

			// RTL support (fixes column on right)
			if ( $table.hasClass( tscss.scrollerRtl ) ) {
				$fixedColumn.addClass( tscss.scrollerRtl );
			}

			$el = $fixedColumn.find( 'tr' );
			len = $el.length;
			for ( index = 0; index < len; index++ ) {
				$el.eq( index ).children( ':gt(' + ( fixedColumns - 1 ) + ')' ).remove();
			}
			$fixedColumn
				.addClass( tscss.scrollerHideElement )
				.prependTo( $wrapper );

			// look for filter widget
			if ( c.$table.hasClass( 'hasFilters' ) ) {
				// make sure fixed column filters aren't disabled
				$el = $fixedColumn
					.find( '.' + tscss.filter )
					.not( '.' + tscss.filterDisabled )
					.prop( 'disabled', false );
				ts.filter.bindSearch( $table, $fixedColumn.find( '.' + tscss.filter ) );
				// disable/enable filters behind fixed column
				$el = $wrapper
					.children( '.' + tscss.scrollerHeader )
					.find( '.' + tscss.filter );
				len = $el.length;
				for ( index = 0; index < len; index++ ) {
					// previously disabled filter; don't mess with it! filterDisabled class added by filter widget
					if ( !$el.eq( index ).hasClass( tscss.filterDisabled || 'disabled' ) ) {
						// disable filters behind fixed column; don't disable visible filters
						$el.eq( index ).prop( 'disabled', index < fixedColumns );
					}
				}
			}

			// disable/enable tab indexes behind fixed column
			c.$table
				.add( '.' + tscss.scrollerFooter + ' table' )
				.children( 'thead' )
				.children( 'tr.' + tscss.headerRow )
				.children()
				.attr( 'tabindex', -1 );

			$el = wo.scroller_$header
				.add( $fixedColumn.find( '.' + tscss.scrollerTable + ' table' ) )
				.children( 'thead' )
				.children( 'tr.' + tscss.headerRow );
			len = $el.length;
			for ( index = 0; index < len; index++ ) {
				temp = $el.eq( index ).children();
				for ( index2 = 0; index2 < temp.length; index2++ ) {
					temp.eq( index2 ).attr( 'tabindex', index2 < fixedColumns ? -1 : 0 );
				}
			}

			ts.bindEvents( c.table, $fixedColumn.find( '.' + tscss.header ) );
			ts.scroller.bindFixedColumnEvents( c, wo );

			/*** Scrollbar hack! Since we can't hide the scrollbar with css ***/
			if ( ts.scroller.isFirefox || ts.scroller.isOldIE ) {
				$fixedTbody.wrap( '<div class="' + tscss.scrollerHack + '" style="overflow:hidden;">' );
			}

		},

		// https://remysharp.com/2010/07/21/throttling-function-calls
		throttle : function(fn, threshhold, scope) {
			threshhold = threshhold || 50;
			var last, deferTimer;
			return function() {
				var context = scope || this,
					now = +(new Date()),
				args = arguments;
				if (last && now < last + threshhold) {
					// hold on to it
					clearTimeout(deferTimer);
					deferTimer = setTimeout(function() {
						last = now;
						fn.apply(context, args);
					}, threshhold);
				} else {
					last = now;
					fn.apply(context, args);
				}
			};
		},

		bindFixedColumnEvents : function( c, wo ) {
			// update thead & tbody in fixed column
			var tsScroller = ts.scroller,
				namespace = c.namespace + 'tsscrollerFixed',
				events = 'scroll' + namespace,
				$fixedTbody = wo.scroller_$fixedColumns.find( '.' + tscss.scrollerTable ),
				fixedScroll = true,
				tableScroll = true;

			c.$table
				.parent()
				// *** SCROLL *** scroll fixed column along with main
				.off( events )
				.on( events, tsScroller.throttle(function() {
					// using flags to prevent firing the scroll event excessively leading to slow scrolling in Firefox
					if ( !wo.scroller_isBusy && fixedScroll ) {
						tableScroll = false;
						var $this = $( this );
						$fixedTbody[0].scrollTop = wo.scroller_saved[1] = $this.scrollTop();
						wo.scroller_saved[0] = $this.scrollLeft();
						setTimeout( function() {
							tableScroll = true;
						}, 20 );
					}
				}));
			// scroll main along with fixed column
			$fixedTbody
				.off( events )
				.on( events, tsScroller.throttle(function() {
					// using flags to prevent firing the scroll event excessively leading to slow scrolling in Firefox
					if ( !wo.scroller_isBusy && tableScroll ) {
						fixedScroll = false;
						c.$table.parent()[0].scrollTop = wo.scroller_saved[1] = $( this ).scrollTop();
						setTimeout( function() {
							fixedScroll = true;
						}, 20 );
					}
				}))
				.scroll();

			// *** ROW HIGHLIGHT ***
			if ( wo.scroller_rowHighlight !== '' ) {
				events = 'mouseover mouseleave '.split( ' ' ).join( namespace + ' ' );
				// can't use c.$tbodies because it doesn't include info-only tbodies
				c.$table
					.off( events, 'tbody > tr' )
					.on( events, 'tbody > tr', function( event ) {
						var indx = c.$table.children( 'tbody' ).children( 'tr' ).index( this );
						$fixedTbody
							.children( 'table' )
							.children( 'tbody' )
							.children( 'tr' )
							.eq( indx )
							.add( this )
							.toggleClass( wo.scroller_rowHighlight, event.type === 'mouseover' );
					});
				$fixedTbody
					.find( 'table' )
					.off( events, 'tbody > tr' )
					.on( events, 'tbody > tr', function( event ) {
						var $fixed = $fixedTbody.children( 'table' ).children( 'tbody' ).children( 'tr' ),
							indx = $fixed.index( this );
						c.$table
							.children( 'tbody' )
							.children( 'tr' )
							.eq( indx )
							.add( this )
							.toggleClass( wo.scroller_rowHighlight, event.type === 'mouseover' );
					});
			}
		},

		adjustWidth : function( c, wo, totalWidth, adj, dir ) {
			var $wrapper = wo.scroller_$container;

			// RTL support (fixes column on right)
			$wrapper
				.children( '.' + tscss.scrollerTable )
				.css( dir ? 'right' : 'left', totalWidth );
			$wrapper
				.children( '.' + tscss.scrollerHeader + ', .' + tscss.scrollerFooter )
				// Safari needs a scrollbar width of extra adjusment to align the fixed & scrolling columns
				.css( dir ? 'right' : 'left', totalWidth + ( dir && ts.scroller.isSafari ? adj : 0 ) );
		},

		updateFixed : function( c, wo ) {
			var temp, adj,
				$wrapper = wo.scroller_$container,
				$hdr = wo.scroller_$header,
				$foot = wo.scroller_$footer,
				$table = c.$table,
				$tableWrap = $table.parent(),
				scrollBarWidth = wo.scroller_barSetWidth,
				dir = $table.hasClass( tscss.scrollerRtl );

			if ( wo.scroller_fixedColumns === 0 ) {
				wo.scroller_isBusy = false;
				ts.scroller.removeFixed( c, wo );
				temp = $wrapper.width();
				$tableWrap.width( temp );
				adj = ts.scroller.hasScrollBar( $tableWrap ) ? scrollBarWidth : 0;
				$hdr
					.parent()
					.add( $foot.parent() )
					.width( temp - adj );
				return;
			}

			if ( !c.isScrolling ) {
				return;
			}

			wo.scroller_isBusy = true;

			// Make sure the wo.scroller_$fixedColumns container exists, if not build it
			if ( !$wrapper.find( '.' + tscss.scrollerFixed ).length ) {
				ts.scroller.setupFixed( c, wo );
			}

			// scroller_fixedColumns
			var index, tbodyIndex, rowIndex, $tbody, $adjCol, $fb, totalRows,

				// source cells for measurement
				$mainTbodies = wo.scroller_$container
					.children( '.' + tscss.scrollerTable )
					.children( 'table' )
					.children( 'tbody' ),
				// variable gets redefined
				$rows = wo.scroller_$header
					.children( 'thead' )
					.children( '.' + tscss.headerRow ),

				// hide fixed column during resize, or we get a FOUC
				$fixedColumn = wo.scroller_$fixedColumns
					.addClass( tscss.scrollerHideElement ),

				// target cells
				$fixedTbodiesTable = $fixedColumn
					.find( '.' + tscss.scrollerTable )
					.children( 'table' ),
				$fixedTbodies = $fixedTbodiesTable
					.children( 'tbody' ),
				// variables
				tsScroller = ts.scroller,
				fixedColumns = wo.scroller_fixedColumns,
				// get dimensions
				getDim = function ($el, name, deflt) {
					return parseInt( $el.css(name) || '', 10 ) || deflt || 0;
				},
				$temp = $table.find( 'tbody td' ),
				borderRightWidth = getDim( $temp, 'border-right-width', 1 ),
				borderSpacing = getDim( $temp, 'border-spacing', 0 ),
				totalWidth = getDim( $table, 'padding-left' ) +
					getDim( $table, 'padding-right' ) +
					// include table left & row left border
					getDim( $table, 'border-left-width', 1 ) * 2 +
					getDim( $table, 'border-right-width', 1 ) -
					borderRightWidth + borderSpacing / 2,
				widths = wo.scroller_calcWidths;

			ts.scroller.removeFixed( c, wo, false );

			// calculate fixed column width
			for ( index = 0; index < fixedColumns; index++ ) {
				totalWidth += widths[ index ] + borderSpacing;
			}

			// set fixed column width
			totalWidth = totalWidth + borderRightWidth * 2;
			tsScroller.setWidth( $fixedColumn.add( $fixedColumn.children() ), totalWidth );
			tsScroller.setWidth( $fixedColumn.children().children( 'table' ), totalWidth );

			// update fixed column tbody content, set cell widths on hidden row
			for ( tbodyIndex = 0; tbodyIndex < c.$tbodies.length; tbodyIndex++ ) {
				$tbody = $mainTbodies.eq( tbodyIndex );
				if ( $tbody.length ) {
					// get tbody
					$rows = $tbody.children();
					totalRows = $rows.length;
					$fb = ts.processTbody( $fixedTbodiesTable, $fixedTbodies.eq( tbodyIndex ), true );
					$fb.empty();
					// update tbody cells after sort/filtering
					for ( rowIndex = 0; rowIndex < totalRows; rowIndex++ ) {
						$adjCol = $( $rows[ rowIndex ].outerHTML );
						$adjCol
							.children( 'td, th' )
							.slice( fixedColumns )
							.remove();
						$fb.append( $adjCol );
					}

					// restore tbody
					ts.processTbody( $fixedTbodiesTable, $fb, false );
				}
			}

			adj = ts.scroller.hasScrollBar( $tableWrap ) ? scrollBarWidth : 0;

			/*** scrollbar HACK! Since we can't hide the scrollbar with css ***/
			if ( tsScroller.isFirefox || tsScroller.isOldIE ) {
				$fixedTbodiesTable
					.css( 'width', totalWidth )
					.parent()
					.css( 'width', totalWidth + adj );
			}

			for ( index = 0; index < fixedColumns; index++ ) {
				temp = ':nth-child(' + ( index + 1 ) + ')';
				$wrapper
					.children( 'div' )
					.children( 'table' )
					.find( 'th' + temp + ', td' + temp + ', col' + temp )
					.addClass( tscss.scrollerHideColumn );
			}
			$fixedColumn
				.removeClass( tscss.scrollerHideElement )
				.find('colgroup')
				.each(function() {
					$(this)
						.find('col:gt(' + (fixedColumns - 1) + ')')
						.addClass( tscss.scrollerHideElement );
				});

			totalWidth = totalWidth - borderRightWidth;
			temp = $tableWrap.parent().innerWidth() - totalWidth;
			$tableWrap.width( temp );
			// RTL support (fixes column on right)
			$wrapper
				.children( '.' + tscss.scrollerTable )
				.css( dir ? 'right' : 'left', totalWidth );
			$wrapper
				.children( '.' + tscss.scrollerHeader + ', .' + tscss.scrollerFooter )
				// Safari needs a scrollbar width of extra adjusment to align the fixed & scrolling columns
				.css( dir ? 'right' : 'left', totalWidth + ( dir && ts.scroller.isSafari ? adj : 0 ) );

			$hdr
				.parent()
				.add( $foot.parent() )
				.width( temp - adj );

			// fix gap under the tbody for the horizontal scrollbar
			temp = ts.scroller.hasScrollBar( $tableWrap, true );
			adj = temp ? scrollBarWidth : 0;
			if ( !$fixedColumn.find( '.' + tscss.scrollerBarSpacer ).length && temp ) {
				$temp = $( '<div class="' + tscss.scrollerBarSpacer + '">' )
					.css( 'height', adj + 'px' );
				$fixedColumn.find( '.' + tscss.scrollerTable ).append( $temp );
			} else if ( !temp ) {
				$fixedColumn.find( '.' + tscss.scrollerBarSpacer ).remove();
			}

			ts.scroller.updateRowHeight( c, wo );
			// set fixed column height (changes with filtering)
			$fixedColumn.height( $wrapper.height() );

			$fixedColumn.removeClass( tscss.scrollerHideElement );

			// adjust caption height, see #1202
			$fixedColumn.find('caption').height( wo.scroller_$header.find( 'caption' ).height() );

			$tableWrap.scroll();
			setTimeout(function() {
				wo.scroller_isBusy = false;
			}, 0);

		},

		fixHeight : function( $rows, $fixedRows ) {
			var index, heightRow, heightFixed, $r, $f,
				addedHt = tscss.scrollerAddedHeight,
				len = $rows.length;
			for ( index = 0; index < len; index++ ) {
				$r = $rows.eq( index );
				$f = $fixedRows.eq( index );
				heightRow = $r.height();
				heightFixed = $f.height();
				if ( heightRow > heightFixed ) {
					$f.addClass( addedHt ).height( heightRow );
				} else if ( heightRow < heightFixed ) {
					$r.addClass( addedHt ).height( heightFixed );
				}
			}
		},

		updateRowHeight : function( c, wo ) {
			var $rows, $fixed,
				$fixedColumns = wo.scroller_$fixedColumns;

			wo.scroller_$container
				.find( '.' + tscss.scrollerAddedHeight )
				.removeClass( tscss.scrollerAddedHeight )
				.height( '' );

			$rows = wo.scroller_$header
				.children( 'thead' )
				.children( 'tr' );
			$fixed = $fixedColumns
				.children( '.' + tscss.scrollerHeader )
				.children( 'table' )
				.children( 'thead' )
				.children( 'tr' );
			ts.scroller.fixHeight( $rows, $fixed );

			$rows = wo.scroller_$footer
				.children( 'tfoot' )
				.children( 'tr' );
			$fixed = $fixedColumns
				.children( '.' + tscss.scrollerFooter )
				.children( 'table' )
				.children( 'tfoot' )
				.children( 'tr' );
			ts.scroller.fixHeight( $rows, $fixed );

			if ( ts.scroller.isFirefox || ts.scroller.isOldIE ) {
				// Firefox/Old IE scrollbar hack (wraps table to hide the scrollbar)
				$fixedColumns = $fixedColumns.find( '.' + tscss.scrollerHack );
			}
			$rows = c.$table
				.children( 'tbody' )
				.children( 'tr' );
			$fixed = $fixedColumns
				.children( '.' + tscss.scrollerTable )
				.children( 'table' )
				.children( 'tbody' )
				.children( 'tr' );
			ts.scroller.fixHeight( $rows, $fixed );

		},

		removeFixed : function( c, wo, removeIt ) {
			var $table = c.$table,
				$wrapper = wo.scroller_$container,
				dir = $table.hasClass( tscss.scrollerRtl );

			// remove fixed columns
			if ( removeIt || typeof removeIt === 'undefined' ) {
				$wrapper.find( '.' + tscss.scrollerFixed ).remove();
			}

			$wrapper
				.find( '.' + tscss.scrollerHideColumn )
				.removeClass( tscss.scrollerHideColumn );

			// RTL support ( fixes column on right )
			$wrapper
				.children( ':not(.' + tscss.scrollerFixed + ')' )
				.css( dir ? 'right' : 'left', 0 );
		},

		remove : function( c, wo ) {
			var $wrap = wo.scroller_$container,
				namespace = c.namespace + 'tsscroller';
			c.$table.off( namespace );
			$( window ).off( namespace );
			if ( $wrap ) {
				c.$table
					.insertBefore( $wrap )
					.find( 'thead' )
					.removeClass( tscss.scrollerHideElement )
					.children( 'tr.' + tscss.headerRow )
					.children()
					.attr( 'tabindex', 0 )
					.end()
					.find( '.' + tscss.filterRow )
					.removeClass( tscss.scrollerHideElement + ' ' + tscss.filterRowHide );
				c.$table
					.find( '.' + tscss.filter )
					.not( '.' + tscss.filterDisabled )
					.prop( 'disabled', false );
				$wrap.remove();
				c.isScrolling = false;
			}
		}

	};

})( jQuery, window );
