/*!
* tablesorter (FORK) pager plugin
* updated 2020-03-03 (v2.31.3)
*/
/*jshint browser:true, jquery:true, unused:false */
;(function($) {
	'use strict';
	/*jshint supernew:true */
	var ts = $.tablesorter;

	$.extend({
		tablesorterPager: new function() {

			this.defaults = {
				// target the pager markup
				container: null,

				// use this format: "http://mydatabase.com?page={page}&size={size}&{sortList:col}&{filterList:fcol}"
				// where {page} is replaced by the page number, {size} is replaced by the number of records to show,
				// {sortList:col} adds the sortList to the url into a "col" array, and {filterList:fcol} adds
				// the filterList to the url into an "fcol" array.
				// So a sortList = [[2,0],[3,0]] becomes "&col[2]=0&col[3]=0" in the url
				// and a filterList = [[2,Blue],[3,13]] becomes "&fcol[2]=Blue&fcol[3]=13" in the url
				ajaxUrl: null,

				// modify the url after all processing has been applied
				customAjaxUrl: function(table, url) { return url; },

				// ajax error callback from $.tablesorter.showError function
				// ajaxError: function( config, xhr, settings, exception ) { return exception; };
				// returning false will abort the error message
				ajaxError: null,

				// modify the $.ajax object to allow complete control over your ajax requests
				ajaxObject: {
					dataType: 'json'
				},

				// set this to false if you want to block ajax loading on init
				processAjaxOnInit: true,

				// process ajax so that the following information is returned:
				// [ total_rows (number), rows (array of arrays), headers (array; optional) ]
				// example:
				// [
				//   100,  // total rows
				//   [
				//     [ "row1cell1", "row1cell2", ... "row1cellN" ],
				//     [ "row2cell1", "row2cell2", ... "row2cellN" ],
				//     ...
				//     [ "rowNcell1", "rowNcell2", ... "rowNcellN" ]
				//   ],
				//   [ "header1", "header2", ... "headerN" ] // optional
				// ]
				ajaxProcessing: function(data) { return data; },

				// output default: '{page}/{totalPages}'
				// possible variables: {size}, {page}, {totalPages}, {filteredPages}, {startRow},
				// {endRow}, {filteredRows} and {totalRows}
				output: '{startRow} to {endRow} of {totalRows} rows', // '{page}/{totalPages}'

				// apply disabled classname to the pager arrows when the rows at either extreme is visible
				updateArrows: true,

				// starting page of the pager (zero based index)
				page: 0,

				// reset pager after filtering; set to desired page #
				// set to false to not change page at filter start
				pageReset: 0,

				// Number of visible rows
				size: 10,

				// Number of options to include in the pager number selector
				maxOptionSize: 20,

				// Save pager page & size if the storage script is loaded (requires $.tablesorter.storage in jquery.tablesorter.widgets.js)
				savePages: true,

				// defines custom storage key
				storageKey: 'tablesorter-pager',

				// if true, the table will remain the same height no matter how many records are displayed. The space is made up by an empty
				// table row set to a height to compensate; default is false
				fixedHeight: false,

				// count child rows towards the set page size? (set true if it is a visible table row within the pager)
				// if true, child row(s) may not appear to be attached to its parent row, may be split across pages or
				// may distort the table if rowspan or cellspans are included.
				countChildRows: false,

				// remove rows from the table to speed up the sort of large tables.
				// setting this to false, only hides the non-visible rows; needed if you plan to add/remove rows with the pager enabled.
				removeRows: false, // removing rows in larger tables speeds up the sort

				// css class names of pager arrows
				cssFirst: '.first', // go to first page arrow
				cssPrev: '.prev', // previous page arrow
				cssNext: '.next', // next page arrow
				cssLast: '.last', // go to last page arrow
				cssGoto: '.gotoPage', // go to page selector - select dropdown that sets the current page
				cssPageDisplay: '.pagedisplay', // location of where the "output" is displayed
				cssPageSize: '.pagesize', // page size selector - select dropdown that sets the "size" option
				cssErrorRow: 'tablesorter-errorRow', // error information row

				// class added to arrows when at the extremes (i.e. prev/first arrows are "disabled" when on the first page)
				cssDisabled: 'disabled', // Note there is no period "." in front of this class name

				// stuff not set by the user
				totalRows: 0,
				totalPages: 0,
				filteredRows: 0,
				filteredPages: 0,
				ajaxCounter: 0,
				currentFilters: [],
				startRow: 0,
				endRow: 0,
				$size: null,
				last: {}

			};

			var pagerEvents = 'filterInit filterStart filterEnd sortEnd disablePager enablePager destroyPager updateComplete ' +
			'pageSize pageSet pageAndSize pagerUpdate refreshComplete ',

			$this = this,

			// hide arrows at extremes
			pagerArrows = function( table, p, disable ) {
				var tmp,
					a = 'addClass',
					r = 'removeClass',
					d = p.cssDisabled,
					dis = !!disable,
					first = ( dis || p.page === 0 ),
					tp = getTotalPages( table, p ),
					last = ( dis || (p.page === tp - 1) || tp === 0 );
				if ( p.updateArrows ) {
					tmp = p.$container.find(p.cssFirst + ',' + p.cssPrev);
					tmp[ first ? a : r ](d); // toggle disabled class
					tmp.each(function() {
						this.ariaDisabled = first;
					});
					tmp = p.$container.find(p.cssNext + ',' + p.cssLast);
					tmp[ last ? a : r ](d);
					tmp.each(function() {
						this.ariaDisabled = last;
					});
				}
			},

			calcFilters = function(table, p) {
				var normalized, indx, len,
				c = table.config,
				hasFilters = c.$table.hasClass('hasFilters');
				if (hasFilters && !p.ajax) {
					if (ts.isEmptyObject(c.cache)) {
						// delayInit: true so nothing is in the cache
						p.filteredRows = p.totalRows = c.$tbodies.eq(0).children('tr').not( p.countChildRows ? '' : '.' + c.cssChildRow ).length;
					} else {
						p.filteredRows = 0;
						normalized = c.cache[0].normalized;
						len = normalized.length;
						for (indx = 0; indx < len; indx++) {
							p.filteredRows += p.regexRows.test(normalized[indx][c.columns].$row[0].className) ? 0 : 1;
						}
					}
				} else if (!hasFilters) {
					p.filteredRows = p.totalRows;
				}
			},

			updatePageDisplay = function(table, p, completed) {
				if ( p.initializing ) { return; }
				var s, t, $out, $el, indx, len, options, output,
				c = table.config,
				namespace = c.namespace + 'pager',
				sz = parsePageSize( p, p.size, 'get' ); // don't allow dividing by zero
				if (sz === 'all') { sz = p.totalRows; }
				if (p.countChildRows) { t[ t.length ] = c.cssChildRow; }
				p.totalPages = Math.ceil( p.totalRows / sz ); // needed for "pageSize" method
				c.totalRows = p.totalRows;
				parsePageNumber( table, p );
				calcFilters(table, p);
				c.filteredRows = p.filteredRows;
				p.filteredPages = Math.ceil( p.filteredRows / sz ) || 0;
				if ( getTotalPages( table, p ) >= 0 ) {
					t = (sz * p.page > p.filteredRows) && completed;
					p.page = (t) ? p.pageReset || 0 : p.page;
					p.startRow = (t) ? sz * p.page + 1 : (p.filteredRows === 0 ? 0 : sz * p.page + 1);
					p.endRow = Math.min( p.filteredRows, p.totalRows, sz * ( p.page + 1 ) );
					$out = p.$container.find(p.cssPageDisplay);

					// Output param can be callback for custom rendering or string
					if (typeof p.output === 'function') {
						s = p.output(table, p);
					} else {
						output = $out
							// get output template from data-pager-output or data-pager-output-filtered
							.attr('data-pager-output' + (p.filteredRows < p.totalRows ? '-filtered' : '')) ||
							p.output;
						// form the output string (can now get a new output string from the server)
						s = ( p.ajaxData && p.ajaxData.output ? p.ajaxData.output || output : output )
							// {page} = one-based index; {page+#} = zero based index +/- value
							.replace(/\{page([\-+]\d+)?\}/gi, function(m, n) {
								return p.totalPages ? p.page + (n ? parseInt(n, 10) : 1) : 0;
							})
							// {totalPages}, {extra}, {extra:0} (array) or {extra : key} (object)
							.replace(/\{\w+(\s*:\s*\w+)?\}/gi, function(m) {
								var len, indx,
								str = m.replace(/[{}\s]/g, ''),
								extra = str.split(':'),
								data = p.ajaxData,
								// return zero for default page/row numbers
								deflt = /(rows?|pages?)$/i.test(str) ? 0 : '';
								if (/(startRow|page)/.test(extra[0]) && extra[1] === 'input') {
									len = ('' + (extra[0] === 'page' ? p.totalPages : p.totalRows)).length;
									indx = extra[0] === 'page' ? p.page + 1 : p.startRow;
									return '<input type="text" class="ts-' + extra[0] + '" style="max-width:' + len + 'em" value="' + indx + '"/>';
								}
								return extra.length > 1 && data && data[extra[0]] ? data[extra[0]][extra[1]] : p[str] || (data ? data[str] : deflt) || deflt;
							});
					}
					$el = p.$container.find(p.cssGoto);
					if ( $el.length ) {
						t = '';
						options = buildPageSelect( table, p );
						len = options.length;
						for (indx = 0; indx < len; indx++) {
							t += '<option value="' + options[indx] + '">' + options[indx] + '</option>';
						}
						// innerHTML doesn't work in IE9 - http://support2.microsoft.com/kb/276228
						$el.html(t).val( p.page + 1 );
					}
					if ($out.length) {
						$out[ ($out[0].nodeName === 'INPUT') ? 'val' : 'html' ](s);
						// rebind startRow/page inputs
						$out.find('.ts-startRow, .ts-page').unbind('change' + namespace).bind('change' + namespace, function() {
							var v = $(this).val(),
							pg = $(this).hasClass('ts-startRow') ? Math.floor( v / sz ) + 1 : v;
							c.$table.triggerHandler('pageSet' + namespace, [ pg ]);
						});
					}
				}
				pagerArrows( table, p );
				fixHeight(table, p);
				if (p.initialized && completed !== false) {
					if (ts.debug(c, 'pager')) {
						console.log('Pager >> Triggering pagerComplete');
					}
					c.$table.triggerHandler('pagerComplete', p);
					// save pager info to storage
					if (p.savePages && ts.storage) {
						ts.storage(table, p.storageKey, {
							page : p.page,
							size : sz === p.totalRows ? 'all' : sz
						});
					}
				}
			},

			buildPageSelect = function( table, p ) {
				// Filter the options page number link array if it's larger than 'maxOptionSize'
				// as large page set links will slow the browser on large dom inserts
				var i, central_focus_size, focus_option_pages, insert_index, option_length, focus_length,
				pg = getTotalPages( table, p ) || 1,
				// make skip set size multiples of 5
				skip_set_size = Math.ceil( ( pg / p.maxOptionSize ) / 5 ) * 5,
				large_collection = pg > p.maxOptionSize,
				current_page = p.page + 1,
				start_page = skip_set_size,
				end_page = pg - skip_set_size,
				option_pages = [ 1 ],
				// construct default options pages array
				option_pages_start_page = (large_collection) ? skip_set_size : 1;

				for ( i = option_pages_start_page; i <= pg; ) {
					option_pages[ option_pages.length ] = i;
					i = i + ( large_collection ? skip_set_size : 1 );
				}
				option_pages[ option_pages.length ] = pg;
				if (large_collection) {
					focus_option_pages = [];
					// don't allow central focus size to be > 5 on either side of current page
					central_focus_size = Math.max( Math.floor( p.maxOptionSize / skip_set_size ) - 1, 5 );

					start_page = current_page - central_focus_size;
					if (start_page < 1) { start_page = 1; }
					end_page = current_page + central_focus_size;
					if (end_page > pg) { end_page = pg; }
					// construct an array to get a focus set around the current page
					for (i = start_page; i <= end_page ; i++) {
						focus_option_pages[ focus_option_pages.length ] = i;
					}

					// keep unique values
					option_pages = $.grep(option_pages, function(value, indx) {
						return $.inArray(value, option_pages) === indx;
					});

					option_length = option_pages.length;
					focus_length = focus_option_pages.length;

					// make sure at all option_pages aren't replaced
					if (option_length - focus_length > skip_set_size / 2 && option_length + focus_length > p.maxOptionSize ) {
						insert_index = Math.floor(option_length / 2) - Math.floor(focus_length / 2);
						Array.prototype.splice.apply(option_pages, [ insert_index, focus_length ]);
					}
					option_pages = option_pages.concat(focus_option_pages);

				}

				// keep unique values again
				option_pages = $.grep(option_pages, function(value, indx) {
					return $.inArray(value, option_pages) === indx;
				})
				.sort(function(a, b) { return a - b; });

				return option_pages;
			},

			fixHeight = function(table, p) {
				var d, h, bs,
				c = table.config,
				$b = c.$tbodies.eq(0);
				$b.find('tr.pagerSavedHeightSpacer').remove();
				if (p.fixedHeight && !p.isDisabled) {
					h = $.data(table, 'pagerSavedHeight');
					if (h) {
						bs = 0;
						if ($(table).css('border-spacing').split(' ').length > 1) {
							bs = $(table).css('border-spacing').split(' ')[1].replace(/[^-\d\.]/g, '');
						}
						d = h - $b.height() + (bs * p.size) - bs;
						if (
							d > 5 && $.data(table, 'pagerLastSize') === p.size &&
							$b.children('tr:visible').length < (p.size === 'all' ? p.totalRows : p.size)
						) {
							$b.append('<tr class="pagerSavedHeightSpacer ' + c.selectorRemove.slice(1) + '" style="height:' + d + 'px;"></tr>');
						}
					}
				}
			},

			changeHeight = function(table, p) {
				var h,
				c = table.config,
				$b = c.$tbodies.eq(0);
				$b.find('tr.pagerSavedHeightSpacer').remove();
				if (!$b.children('tr:visible').length) {
					$b.append('<tr class="pagerSavedHeightSpacer ' + c.selectorRemove.slice(1) + '"><td>&nbsp</td></tr>');
				}
				h = $b.children('tr').eq(0).height() * (p.size === 'all' ? p.totalRows : p.size);
				$.data(table, 'pagerSavedHeight', h);
				fixHeight(table, p);
				$.data(table, 'pagerLastSize', p.size);
			},

			hideRows = function(table, p) {
				if (!p.ajaxUrl) {
					var i,
					lastIndex = 0,
					c = table.config,
					rows = c.$tbodies.eq(0).children('tr'),
					l = rows.length,
					sz = p.size === 'all' ? p.totalRows : p.size,
					s = ( p.page * sz ),
					e =  s + sz,
					last = -1, // for cache indexing
					j = 0; // size counter
					p.cacheIndex = [];
					for ( i = 0; i < l; i++ ) {
						if ( !p.regexFiltered.test(rows[i].className) ) {
							if (j === s && rows[i].className.match(c.cssChildRow)) {
								// hide child rows @ start of pager (if already visible)
								rows[i].style.display = 'none';
							} else {
								rows[i].style.display = ( j >= s && j < e ) ? '' : 'none';
								if (last !== j && j >= s && j < e) {
									p.cacheIndex[ p.cacheIndex.length ] = i;
									last = j;
								}
								// don't count child rows
								j += rows[i].className.match(c.cssChildRow + '|' + c.selectorRemove.slice(1)) && !p.countChildRows ? 0 : 1;
								if ( j === e && rows[i].style.display !== 'none' && rows[i].className.match(ts.css.cssHasChild) ) {
									lastIndex = i;
								}
							}
						}
					}
					// add any attached child rows to last row of pager. Fixes part of issue #396
					if ( lastIndex > 0 && rows[lastIndex].className.match(ts.css.cssHasChild) ) {
						while ( ++lastIndex < l && rows[lastIndex].className.match(c.cssChildRow) ) {
							rows[lastIndex].style.display = '';
						}
					}
				}
			},

			hideRowsSetup = function(table, p) {
				p.size = parsePageSize( p, p.$container.find(p.cssPageSize).val(), 'get' );
				setPageSize( table, p.size, p );
				pagerArrows( table, p );
				if ( !p.removeRows ) {
					hideRows(table, p);
					$(table).bind('sortEnd filterEnd '.split(' ').join(table.config.namespace + 'pager '), function() {
						hideRows(table, p);
					});
				}
			},

			renderAjax = function(data, table, p, xhr, settings, exception) {
				// process data
				if ( typeof p.ajaxProcessing === 'function' ) {

					// in case nothing is returned by ajax, empty out the table; see #1032
					// but do it before calling pager_ajaxProcessing because that function may add content
					// directly to the table
					table.config.$tbodies.eq(0).empty();

					// ajaxProcessing result: [ total, rows, headers ]
					var i, j, t, hsh, $f, $sh, $headers, $h, icon, th, d, l, rr_count, len, sz,
					c = table.config,
					$table = c.$table,
					tds = '',
					result = p.ajaxProcessing(data, table, xhr) || [ 0, [] ];
					// Clean up any previous error.
					ts.showError( table );

					if ( exception ) {
						if (ts.debug(c, 'pager')) {
							console.error('Pager >> Ajax Error', xhr, settings, exception);
						}
						ts.showError( table, xhr, settings, exception );
						c.$tbodies.eq(0).children('tr').detach();
						p.totalRows = 0;
					} else {
						// process ajax object
						if (!$.isArray(result)) {
							p.ajaxData = result;
							c.totalRows = p.totalRows = result.total;
							c.filteredRows = p.filteredRows = typeof result.filteredRows !== 'undefined' ? result.filteredRows : result.total;
							th = result.headers;
							d = result.rows || [];
						} else {
							// allow [ total, rows, headers ]  or [ rows, total, headers ]
							t = isNaN(result[0]) && !isNaN(result[1]);
							// ensure a zero returned row count doesn't fail the logical ||
							rr_count = result[t ? 1 : 0];
							p.totalRows = isNaN(rr_count) ? p.totalRows || 0 : rr_count;
							// can't set filtered rows when returning an array
							c.totalRows = c.filteredRows = p.filteredRows = p.totalRows;
							// set row data to empty array if nothing found - see http://stackoverflow.com/q/30875583/145346
							d = p.totalRows === 0 ? [] : result[t ? 0 : 1] || []; // row data
							th = result[2]; // headers
						}
						l = d && d.length;
						if (d instanceof $) {
							if (p.processAjaxOnInit) {
								// append jQuery object
								c.$tbodies.eq(0).empty();
								c.$tbodies.eq(0).append(d);
							}
						} else if (l) {
							// build table from array
							for ( i = 0; i < l; i++ ) {
								tds += '<tr>';
								for ( j = 0; j < d[i].length; j++ ) {
									// build tbody cells; watch for data containing HTML markup - see #434
									tds += /^\s*<td/.test(d[i][j]) ? $.trim(d[i][j]) : '<td>' + d[i][j] + '</td>';
								}
								tds += '</tr>';
							}
							// add rows to first tbody
							if (p.processAjaxOnInit) {
								c.$tbodies.eq(0).html( tds );
							}
						}
						p.processAjaxOnInit = true;
						// update new header text
						if ( th ) {
							hsh = $table.hasClass('hasStickyHeaders');
							$sh = hsh ?
								c.widgetOptions.$sticky.children('thead:first').children('tr:not(.' + c.cssIgnoreRow + ')').children() :
								'';
							$f = $table.find('tfoot tr:first').children();
							// don't change td headers (may contain pager)
							$headers = c.$headers.filter( 'th ' );
							len = $headers.length;
							for ( j = 0; j < len; j++ ) {
								$h = $headers.eq( j );
								// add new test within the first span it finds, or just in the header
								if ( $h.find('.' + ts.css.icon).length ) {
									icon = $h.find('.' + ts.css.icon).clone(true);
									$h.find('.' + ts.css.headerIn).html( th[j] ).append(icon);
									if ( hsh && $sh.length ) {
										icon = $sh.eq(j).find('.' + ts.css.icon).clone(true);
										$sh.eq(j).find('.' + ts.css.headerIn).html( th[j] ).append(icon);
									}
								} else {
									$h.find('.' + ts.css.headerIn).html( th[j] );
									if (hsh && $sh.length) {
										// add sticky header to container just in case it contains pager controls
										p.$container = p.$container.add( c.widgetOptions.$sticky );
										$sh.eq(j).find('.' + ts.css.headerIn).html( th[j] );
									}
								}
								$f.eq(j).html( th[j] );
							}
						}
					}
					if (c.showProcessing) {
						ts.isProcessing(table); // remove loading icon
					}
					sz = parsePageSize( p, p.size, 'get' );
					// make sure last pager settings are saved, prevents multiple server side calls with
					// the same parameters
					p.totalPages = sz === 'all' ? 1 : Math.ceil( p.totalRows / sz );
					p.last.totalRows = p.totalRows;
					p.last.currentFilters = p.currentFilters;
					p.last.sortList = (c.sortList || []).join(',');
					updatePageDisplay(table, p, false);
					// tablesorter core updateCache (not pager)
					ts.updateCache( c, function() {
						if (p.initialized) {
							// apply widgets after table has rendered & after a delay to prevent
							// multiple applyWidget blocking code from blocking this trigger
							setTimeout(function() {
								if (ts.debug(c, 'pager')) {
									console.log('Pager >> Triggering pagerChange');
								}
								$table.triggerHandler( 'pagerChange', p );
								ts.applyWidget( table );
								updatePageDisplay(table, p, true);
							}, 0);
						}
					});

				}
				if (!p.initialized) {
					pagerInitialized(table, p);
				}
			},

			getAjax = function(table, p) {
				var url = getAjaxUrl(table, p),
				$doc = $(document),
				counter,
				c = table.config,
				namespace = c.namespace + 'pager';
				if ( url !== '' ) {
					if (c.showProcessing) {
						ts.isProcessing(table, true); // show loading icon
					}
					$doc.bind('ajaxError' + namespace, function(e, xhr, settings, exception) {
						renderAjax(null, table, p, xhr, settings, exception);
						$doc.unbind('ajaxError' + namespace);
					});

					counter = ++p.ajaxCounter;

					p.last.ajaxUrl = url; // remember processed url
					p.ajaxObject.url = url; // from the ajaxUrl option and modified by customAjaxUrl
					p.ajaxObject.success = function(data, status, jqxhr) {
						// Refuse to process old ajax commands that were overwritten by new ones - see #443
						if (counter < p.ajaxCounter) {
							return;
						}
						renderAjax(data, table, p, jqxhr);
						$doc.unbind('ajaxError' + namespace);
						if (typeof p.oldAjaxSuccess === 'function') {
							p.oldAjaxSuccess(data);
						}
					};
					if (ts.debug(c, 'pager')) {
						console.log('Pager >> Ajax initialized', p.ajaxObject);
					}
					$.ajax(p.ajaxObject);
				}
			},

			getAjaxUrl = function(table, p) {
				var indx, len,
				c = table.config,
				url = (p.ajaxUrl) ? p.ajaxUrl
				// allow using "{page+1}" in the url string to switch to a non-zero based index
				.replace(/\{page([\-+]\d+)?\}/, function(s, n) { return p.page + (n ? parseInt(n, 10) : 0); })
				// this will pass "all" to server when size is set to "all"
				.replace(/\{size\}/g, p.size) : '',
				sortList = c.sortList,
				filterList = p.currentFilters || $(table).data('lastSearch') || [],
				sortCol = url.match(/\{\s*sort(?:List)?\s*:\s*(\w*)\s*\}/),
				filterCol = url.match(/\{\s*filter(?:List)?\s*:\s*(\w*)\s*\}/),
				arry = [];
				if (sortCol) {
					sortCol = sortCol[1];
					len = sortList.length;
					for (indx = 0; indx < len; indx++) {
						arry[ arry.length ] = sortCol + '[' + sortList[indx][0] + ']=' + sortList[indx][1];
					}
					// if the arry is empty, just add the col parameter... "&{sortList:col}" becomes "&col"
					url = url.replace(/\{\s*sort(?:List)?\s*:\s*(\w*)\s*\}/g, arry.length ? arry.join('&') : sortCol );
					arry = [];
				}
				if (filterCol) {
					filterCol = filterCol[1];
					len = filterList.length;
					for (indx = 0; indx < len; indx++) {
						if (filterList[indx]) {
							arry[ arry.length ] = filterCol + '[' + indx + ']=' + encodeURIComponent( filterList[indx] );
						}
					}
					// if the arry is empty, just add the fcol parameter... "&{filterList:fcol}" becomes "&fcol"
					url = url.replace(/\{\s*filter(?:List)?\s*:\s*(\w*)\s*\}/g, arry.length ? arry.join('&') : filterCol );
					p.currentFilters = filterList;
				}
				if ( typeof p.customAjaxUrl === 'function' ) {
					url = p.customAjaxUrl(table, url);
				}
				if (ts.debug(c, 'pager')) {
					console.log('Pager >> Ajax url = ' + url);
				}
				return url;
			},

			renderTable = function(table, rows, p) {
				var $tb, index, count, added,
				$t = $(table),
				c = table.config,
				debug = ts.debug(c, 'pager'),
				f = c.$table.hasClass('hasFilters'),
				l = rows && rows.length || 0, // rows may be undefined
				e = p.size === 'all' ? p.totalRows : p.size,
				s = ( p.page * e );
				if ( l < 1 ) {
					if (debug) {
						console.warn('Pager >> No rows for pager to render');
					}
					// empty table, abort!
					return;
				}
				if ( p.page >= p.totalPages ) {
					// lets not render the table more than once
					moveToLastPage(table, p);
				}
				p.cacheIndex = [];
				p.isDisabled = false; // needed because sorting will change the page and re-enable the pager
				if (p.initialized) {
					if (debug) {
						console.log('Pager >> Triggering pagerChange');
					}
					$t.triggerHandler( 'pagerChange', p );
				}
				if ( !p.removeRows ) {
					hideRows(table, p);
				} else {
					ts.clearTableBody(table);
					$tb = ts.processTbody(table, c.$tbodies.eq(0), true);
					// not filtered, start from the calculated starting point (s)
					// if filtered, start from zero
					index = f ? 0 : s;
					count = f ? 0 : s;
					added = 0;
					while (added < e && index < rows.length) {
						if (!f || !p.regexFiltered.test(rows[index][0].className)) {
							count++;
							if (count > s && added <= e) {
								added++;
								p.cacheIndex[ p.cacheIndex.length ] = index;
								$tb.append(rows[index]);
							}
						}
						index++;
					}
					ts.processTbody(table, $tb, false);
				}
				updatePageDisplay(table, p);
				if (table.isUpdating) {
					if (debug) {
						console.log('Pager >> Triggering updateComplete');
					}
					$t.triggerHandler('updateComplete', [ table, true ]);
				}
			},

			showAllRows = function(table, p) {
				var index, $controls, len;
				if ( p.ajax ) {
					pagerArrows( table, p, true );
				} else {
					$.data(table, 'pagerLastPage', p.page);
					$.data(table, 'pagerLastSize', p.size);
					p.page = 0;
					p.size = p.totalRows;
					p.totalPages = 1;
					$(table)
						.addClass('pagerDisabled')
						.removeAttr('aria-describedby')
						.find('tr.pagerSavedHeightSpacer').remove();
					renderTable(table, table.config.rowsCopy, p);
					p.isDisabled = true;
					ts.applyWidget( table );
					if (ts.debug(table.config, 'pager')) {
						console.log('Pager >> Disabled');
					}
				}
				// disable size selector
				$controls = p.$container.find( p.cssGoto + ',' + p.cssPageSize + ', .ts-startRow, .ts-page' );
				len = $controls.length;
				for ( index = 0; index < len; index++ ) {
					$controls.eq( index ).addClass( p.cssDisabled )[0].disabled = true;
					$controls[ index ].ariaDisabled = true;
				}
			},

			// updateCache if delayInit: true
			updateCache = function(table) {
				var c = table.config,
				p = c.pager;
				// tablesorter core updateCache (not pager)
				ts.updateCache( c, function() {
					var i,
					rows = [],
					n = table.config.cache[0].normalized;
					p.totalRows = n.length;
					for (i = 0; i < p.totalRows; i++) {
						rows[ rows.length ] = n[i][c.columns].$row;
					}
					c.rowsCopy = rows;
					moveToPage(table, p, true);
				});
			},

			moveToPage = function(table, p, pageMoved) {
				if ( p.isDisabled ) { return; }
				var tmp,
					c = table.config,
					debug = ts.debug(c, 'pager'),
					$t = $(table),
					l = p.last;
				if ( pageMoved !== false && p.initialized && ts.isEmptyObject(c.cache)) {
					return updateCache(table);
				}
				// abort page move if the table has filters and has not been initialized
				if (p.ajax && ts.hasWidget(table, 'filter') && !c.widgetOptions.filter_initialized) { return; }
				parsePageNumber( table, p );
				calcFilters(table, p);
				// fixes issue where one currentFilter is [] and the other is ['','',''],
				// making the next if comparison think the filters are different (joined by commas). Fixes #202.
				l.currentFilters = (l.currentFilters || []).join('') === '' ? [] : l.currentFilters;
				p.currentFilters = (p.currentFilters || []).join('') === '' ? [] : p.currentFilters;
				// don't allow rendering multiple times on the same page/size/totalRows/filters/sorts
				if ( l.page === p.page && l.size === p.size && l.totalRows === p.totalRows &&
				(l.currentFilters || []).join(',') === (p.currentFilters || []).join(',') &&
				// check for ajax url changes see #730
				(l.ajaxUrl || '') === (p.ajaxObject.url || '') &&
				// & ajax url option changes (dynamically add/remove/rename sort & filter parameters)
				(l.optAjaxUrl || '') === (p.ajaxUrl || '') &&
				l.sortList === (c.sortList || []).join(',') ) { return; }
				if (debug) {
					console.log('Pager >> Changing to page ' + p.page);
				}
				p.last = {
					page : p.page,
					size : p.size,
					// fixes #408; modify sortList otherwise it auto-updates
					sortList : (c.sortList || []).join(','),
					totalRows : p.totalRows,
					currentFilters : p.currentFilters || [],
					ajaxUrl : p.ajaxObject.url || '',
					optAjaxUrl : p.ajaxUrl || ''
				};
				if (p.ajax) {
					if ( !p.processAjaxOnInit && !ts.isEmptyObject(p.initialRows) ) {
						p.processAjaxOnInit = true;
						tmp = p.initialRows;
						p.totalRows = typeof tmp.total !== 'undefined' ? tmp.total :
						( debug ? console.error('Pager >> No initial total page set!') || 0 : 0 );
						p.filteredRows = typeof tmp.filtered !== 'undefined' ? tmp.filtered :
						( debug ? console.error('Pager >> No initial filtered page set!') || 0 : 0 );
						pagerInitialized( table, p );
					} else {
						getAjax(table, p);
					}
				} else if (!p.ajax) {
					renderTable(table, c.rowsCopy, p);
				}
				$.data(table, 'pagerLastPage', p.page);
				if (p.initialized && pageMoved !== false) {
					if (debug) {
						console.log('Pager >> Triggering pageMoved');
					}
					$t.triggerHandler('pageMoved', p);
					ts.applyWidget( table );
					if (table.isUpdating) {
						if (debug) {
							console.log('Pager >> Triggering updateComplete');
						}
						$t.triggerHandler('updateComplete', [ table, true ]);
					}
				}
			},

			getTotalPages = function( table, p ) {
				return ts.hasWidget( table, 'filter' ) ?
					Math.min( p.totalPages, p.filteredPages ) :
					p.totalPages;
			},

			parsePageNumber = function( table, p ) {
				var min = getTotalPages( table, p ) - 1;
				p.page = parseInt( p.page, 10 );
				if ( p.page < 0 || isNaN( p.page ) ) { p.page = 0; }
				if ( p.page > min && min >= 0 ) { p.page = min; }
				return p.page;
			},

			// set to either set or get value
			parsePageSize = function( p, size, mode ) {
				var s = parseInt( size, 10 ) || p.size || p.settings.size || 10;
				if (p.initialized && (/all/i.test( s + ' ' + size ) || s === p.totalRows)) {
					// Fixing #1364 & #1366
					return p.$container.find(p.cssPageSize + ' option[value="all"]').length ?
						'all' : p.totalRows;
				}
				// "get" to get `p.size` or "set" to set `pageSize.val()`
				return mode === 'get' ? s : p.size;
			},

			setPageSize = function(table, size, p) {
				// "all" size is only returned if an "all" option exists - fixes #1366
				p.size = parsePageSize( p, size, 'get' );
				p.$container.find( p.cssPageSize ).val( p.size );
				$.data(table, 'pagerLastPage', parsePageNumber( table, p ) );
				$.data(table, 'pagerLastSize', p.size);
				p.totalPages = p.size === 'all' ? 1 : Math.ceil( p.totalRows / p.size );
				p.filteredPages = p.size === 'all' ? 1 : Math.ceil( p.filteredRows / p.size );
			},

			moveToFirstPage = function(table, p) {
				p.page = 0;
				moveToPage(table, p);
			},

			moveToLastPage = function(table, p) {
				p.page = getTotalPages( table, p ) - 1;
				moveToPage(table, p);
			},

			moveToNextPage = function(table, p) {
				p.page++;
				var last = getTotalPages( table, p ) - 1;
				if ( p.page >= last ) {
					p.page = last;
				}
				moveToPage(table, p);
			},

			moveToPrevPage = function(table, p) {
				p.page--;
				if ( p.page <= 0 ) {
					p.page = 0;
				}
				moveToPage(table, p);
			},

			pagerInitialized = function(table, p) {
				p.initialized = true;
				p.initializing = false;
				if (ts.debug(table.config, 'pager')) {
					console.log('Pager >> Triggering pagerInitialized');
				}
				$(table).triggerHandler( 'pagerInitialized', p );
				ts.applyWidget( table );
				updatePageDisplay(table, p);
			},

			resetState = function(table, p) {
				var c = table.config;
				c.pager = $.extend( true, {}, $.tablesorterPager.defaults, p.settings );
				init(table, p.settings);
			},

			destroyPager = function(table, p) {
				var c = table.config,
				namespace = c.namespace + 'pager',
				ctrls = [ p.cssFirst, p.cssPrev, p.cssNext, p.cssLast, p.cssGoto, p.cssPageSize ].join( ',' );
				showAllRows(table, p);
				p.$container
				// hide pager controls
				.hide()
				// unbind
				.find( ctrls )
				.unbind( namespace );
				c.appender = null; // remove pager appender function
				c.$table.unbind( namespace );
				if (ts.storage) {
					ts.storage(table, p.storageKey, '');
				}
				delete c.pager;
				delete c.rowsCopy;
			},

			enablePager = function(table, p, triggered) {
				var info, size, $el,
				c = table.config;
				p.$container.find(p.cssGoto + ',' + p.cssPageSize + ',.ts-startRow, .ts-page')
				.removeClass(p.cssDisabled)
				.removeAttr('disabled')
				.each(function() {
					this.ariaDisabled = false;
				});
				p.isDisabled = false;
				p.page = $.data(table, 'pagerLastPage') || p.page || 0;
				$el = p.$container.find(p.cssPageSize);
				size = $el.find('option[selected]').val();
				p.size = $.data(table, 'pagerLastSize') || parsePageSize( p, size, 'get' );
				p.totalPages = p.size === 'all' ? 1 : Math.ceil( getTotalPages( table, p ) / p.size );
				setPageSize(table, p.size, p); // set page size
				// if table id exists, include page display with aria info
				if ( table.id && !c.$table.attr( 'aria-describedby' ) ) {
					$el = p.$container.find( p.cssPageDisplay );
					info = $el.attr( 'id' );
					if ( !info ) {
						// only add pageDisplay id if it doesn't exist - see #1288
						info = table.id + '_pager_info';
						$el.attr( 'id', info );
					}
					c.$table.attr( 'aria-describedby', info );
				}
				changeHeight(table, p);
				if ( triggered ) {
					// tablesorter core update table
					ts.update( c );
					setPageSize(table, p.size, p);
					moveToPage(table, p);
					hideRowsSetup(table, p);
					if (ts.debug(c, 'pager')) {
						console.log('Pager >> Enabled');
					}
				}
			},

			init = function(table, settings) {
				var t, ctrls, fxn, $el,
				c = table.config,
				wo = c.widgetOptions,
				debug = ts.debug(c, 'pager'),
				p = c.pager = $.extend( true, {}, $.tablesorterPager.defaults, settings ),
				$t = c.$table,
				namespace = c.namespace + 'pager',
				// added in case the pager is reinitialized after being destroyed.
				pager = p.$container = $(p.container).addClass('tablesorter-pager').show();
				// save a copy of the original settings
				p.settings = $.extend( true, {}, $.tablesorterPager.defaults, settings );
				if (debug) {
					console.log('Pager >> Initializing');
				}
				p.oldAjaxSuccess = p.oldAjaxSuccess || p.ajaxObject.success;
				c.appender = $this.appender;
				p.initializing = true;
				if (p.savePages && ts.storage) {
					t = ts.storage(table, p.storageKey) || {}; // fixes #387
					p.page = isNaN(t.page) ? p.page : t.page;
					p.size = t.size === 'all' ? t.size : ( isNaN( t.size ) ? p.size : t.size ) || p.setSize || 10;
					setPageSize(table, p.size, p);
				}
				// skipped rows
				p.regexRows = new RegExp('(' + (wo.filter_filteredRow || 'filtered') + '|' + c.selectorRemove.slice(1) + '|' + c.cssChildRow + ')');
				p.regexFiltered = new RegExp(wo.filter_filteredRow || 'filtered');

				$t
				// .unbind( namespace ) adding in jQuery 1.4.3 ( I think )
				.unbind( pagerEvents.split(' ').join(namespace + ' ').replace(/\s+/g, ' ') )
				.bind('filterInit filterStart '.split(' ').join(namespace + ' '), function(e, filters) {
					p.currentFilters = $.isArray(filters) ? filters : c.$table.data('lastSearch');
					var filtersEqual;
					if (p.ajax && e.type === 'filterInit') {
						// ensure pager ajax is called after filter widget has initialized
						return moveToPage( table, p, false );
					}
					if (ts.filter.equalFilters) {
						filtersEqual = ts.filter.equalFilters(c, c.lastSearch, p.currentFilters);
					} else {
						// will miss filter changes of the same value in a different column, see #1363
						filtersEqual = (c.lastSearch || []).join('') !== (p.currentFilters || []).join('');
					}
					// don't change page if filters are the same (pager updating, etc)
					if (e.type === 'filterStart' && p.pageReset !== false && !filtersEqual) {
						p.page = p.pageReset; // fixes #456 & #565
					}
				})
				// update pager after filter widget completes
				.bind('filterEnd sortEnd '.split(' ').join(namespace + ' '), function() {
					p.currentFilters = c.$table.data('lastSearch');
					if (p.initialized || p.initializing) {
						if (c.delayInit && c.rowsCopy && c.rowsCopy.length === 0) {
							// make sure we have a copy of all table rows once the cache has been built
							updateCache(table);
						}
						updatePageDisplay(table, p, false);
						moveToPage(table, p, false);
						ts.applyWidget( table );
					}
				})
				.bind('disablePager' + namespace, function(e) {
					e.stopPropagation();
					showAllRows(table, p);
				})
				.bind('enablePager' + namespace, function(e) {
					e.stopPropagation();
					enablePager(table, p, true);
				})
				.bind('destroyPager' + namespace, function(e) {
					e.stopPropagation();
					destroyPager(table, p);
				})
				.bind('resetToLoadState' + namespace, function(e) {
					e.stopPropagation();
					resetState(table, p);
				})
				.bind('updateComplete' + namespace, function(e, table, triggered) {
					e.stopPropagation();
					// table can be unintentionally undefined in tablesorter v2.17.7 and earlier
					// don't recalculate total rows/pages if using ajax
					if ( !table || triggered || p.ajax ) { return; }
					var $rows = c.$tbodies.eq(0).children('tr').not(c.selectorRemove);
					p.totalRows = $rows.length - ( p.countChildRows ? 0 : $rows.filter('.' + c.cssChildRow).length );
					p.totalPages = p.size === 'all' ? 1 : Math.ceil( p.totalRows / p.size );
					if ($rows.length && c.rowsCopy && c.rowsCopy.length === 0) {
						// make a copy of all table rows once the cache has been built
						updateCache(table);
					}
					if ( p.page >= p.totalPages ) {
						moveToLastPage(table, p);
					}
					hideRows(table, p);
					changeHeight(table, p);
					updatePageDisplay(table, p, true);
				})
				.bind('pageSize refreshComplete '.split(' ').join(namespace + ' '), function(e, size) {
					e.stopPropagation();
					setPageSize(table, parsePageSize( p, size, 'get' ), p);
					moveToPage(table, p);
					hideRows(table, p);
					updatePageDisplay(table, p, false);
				})
				.bind('pageSet pagerUpdate '.split(' ').join(namespace + ' '), function(e, num) {
					e.stopPropagation();
					// force pager refresh
					if (e.type === 'pagerUpdate') {
						num = typeof num === 'undefined' ? p.page + 1 : num;
						p.last.page = true;
					}
					p.page = (parseInt(num, 10) || 1) - 1;
					moveToPage(table, p, true);
					updatePageDisplay(table, p, false);
				})
				.bind('pageAndSize' + namespace, function(e, page, size) {
					e.stopPropagation();
					p.page = (parseInt(page, 10) || 1) - 1;
					setPageSize(table, parsePageSize( p, size, 'get' ), p);
					moveToPage(table, p, true);
					hideRows(table, p);
					updatePageDisplay(table, p, false);
				});

				// clicked controls
				ctrls = [ p.cssFirst, p.cssPrev, p.cssNext, p.cssLast ];
				fxn = [ moveToFirstPage, moveToPrevPage, moveToNextPage, moveToLastPage ];
				if (debug && !pager.length) {
					console.warn('Pager >> "container" not found');
				}
				pager.find(ctrls.join(','))
				.attr('tabindex', 0)
				.unbind('click' + namespace)
				.bind('click' + namespace, function(e) {
					e.stopPropagation();
					var i, $t = $(this), l = ctrls.length;
					if ( !$t.hasClass(p.cssDisabled) ) {
						for (i = 0; i < l; i++) {
							if ($t.is(ctrls[i])) {
								fxn[i](table, p);
								break;
							}
						}
					}
				});

				// goto selector
				$el = pager.find(p.cssGoto);
				if ( $el.length ) {
					$el
					.unbind('change' + namespace)
					.bind('change' + namespace, function() {
						p.page = $(this).val() - 1;
						moveToPage(table, p, true);
						updatePageDisplay(table, p, false);
					});
				} else if (debug) {
					console.warn('Pager >> "goto" selector not found');
				}
				// page size selector
				$el = pager.find(p.cssPageSize);
				if ( $el.length ) {
					// setting an option as selected appears to cause issues with initial page size
					$el.find('option').removeAttr('selected');
					$el.unbind('change' + namespace).bind('change' + namespace, function() {
						if ( !$(this).hasClass(p.cssDisabled) ) {
							var size = $(this).val();
							// in case there are more than one pager
							setPageSize(table, size, p);
							moveToPage(table, p);
							changeHeight(table, p);
						}
						return false;
					});
				} else if (debug) {
					console.warn('Pager >> "size" selector not found');
				}

				// clear initialized flag
				p.initialized = false;
				// before initialization event
				$t.triggerHandler('pagerBeforeInitialized', p);

				enablePager(table, p, false);
				if ( typeof p.ajaxUrl === 'string' ) {
					// ajax pager; interact with database
					p.ajax = true;
					// When filtering with ajax, allow only custom filtering function, disable default
					// filtering since it will be done server side.
					c.widgetOptions.filter_serversideFiltering = true;
					c.serverSideSorting = true;
					moveToPage(table, p);
				} else {
					p.ajax = false;
					// Regular pager; all rows stored in memory
					ts.appendCache( c, true ); // true = don't apply widgets
					hideRowsSetup(table, p);
				}

				// pager initialized
				if (!p.ajax && !p.initialized) {
					p.initializing = false;
					p.initialized = true;
					// update page size on init
					setPageSize(table, p.size, p);
					moveToPage(table, p);
					if (debug) {
						console.log('Pager >> Triggering pagerInitialized');
					}
					c.$table.triggerHandler( 'pagerInitialized', p );
					if ( !( c.widgetOptions.filter_initialized && ts.hasWidget(table, 'filter') ) ) {
						updatePageDisplay(table, p, false);
					}
				}

				// make the hasWidget function think that the pager widget is being used
				c.widgetInit.pager = true;
			};

			$this.appender = function(table, rows) {
				var c = table.config,
				p = c.pager;
				if ( !p.ajax ) {
					c.rowsCopy = rows;
					p.totalRows = p.countChildRows ? c.$tbodies.eq(0).children('tr').length : rows.length;
					p.size = $.data(table, 'pagerLastSize') || p.size || p.settings.size || 10;
					p.totalPages = p.size === 'all' ? 1 : Math.ceil( p.totalRows / p.size );
					renderTable(table, rows, p);
					// update display here in case all rows are removed
					updatePageDisplay(table, p, false);
				}
			};

			$this.construct = function(settings) {
				return this.each(function() {
					// check if tablesorter has initialized
					if (!(this.config && this.hasInitialized)) { return; }
					init(this, settings);
				});
			};

		}()
	});

	// see #486
	ts.showError = function( table, xhr, settings, exception ) {
		var $table = $( table ),
			c = $table[0].config,
			wo = c && c.widgetOptions,
			errorRow = c.pager && c.pager.cssErrorRow ||
			wo && wo.pager_css && wo.pager_css.errorRow ||
			'tablesorter-errorRow',
			typ = typeof xhr,
			valid = true,
			message = '',
			removeRow = function() {
				c.$table.find( 'thead' ).find( c.selectorRemove ).remove();
			};

		if ( !$table.length ) {
			console.error('tablesorter showError: no table parameter passed');
			return;
		}

		// ajaxError callback for plugin or widget - see #992
		if ( typeof c.pager.ajaxError === 'function' ) {
			valid = c.pager.ajaxError( c, xhr, settings, exception );
			if ( valid === false ) {
				return removeRow();
			} else {
				message = valid;
			}
		} else if ( typeof wo.pager_ajaxError === 'function' ) {
			valid = wo.pager_ajaxError( c, xhr, settings, exception );
			if ( valid === false ) {
				return removeRow();
			} else {
				message = valid;
			}
		}

		if ( message === '' ) {
			if ( typ === 'object' ) {
				message =
					xhr.status === 0 ? 'Not connected, verify Network' :
					xhr.status === 404 ? 'Requested page not found [404]' :
					xhr.status === 500 ? 'Internal Server Error [500]' :
					exception === 'parsererror' ? 'Requested JSON parse failed' :
					exception === 'timeout' ? 'Time out error' :
					exception === 'abort' ? 'Ajax Request aborted' :
					'Uncaught error: ' + xhr.statusText + ' [' + xhr.status + ']';
			} else if ( typ === 'string'  ) {
				// keep backward compatibility (external usage just passes a message string)
				message = xhr;
			} else {
				// remove all error rows
				return removeRow();
			}
		}

		// allow message to include entire row HTML!
		$( /tr\>/.test(message) ? message : '<tr><td colspan="' + c.columns + '">' + message + '</td></tr>' )
			.click( function() {
				$( this ).remove();
			})
			// add error row to thead instead of tbody, or clicking on the header will result in a parser error
			.appendTo( c.$table.find( 'thead:first' ) )
			.addClass( errorRow + ' ' + c.selectorRemove.slice(1) )
			.attr({
				role : 'alert',
				'aria-live' : 'assertive'
			});

	};

	// extend plugin scope
	$.fn.extend({
		tablesorterPager: $.tablesorterPager.construct
	});

})(jQuery);
