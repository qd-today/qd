/*! Widget: output - updated 9/27/2017 (v2.29.0) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * Modified from:
 * HTML Table to CSV: http://www.kunalbabre.com/projects/table2CSV.php (License unknown?)
 * Download-File-JS: https://github.com/PixelsCommander/Download-File-JS (http://www.apache.org/licenses/LICENSE-2.0)
 * FileSaver.js: https://github.com/eligrey/FileSaver.js (MIT)
 */
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery:false, alert:false */
;(function($) {
	'use strict';

	var ts = $.tablesorter,

	output = ts.output = {

		event      : 'outputTable',
		// Double click time is about 500ms; this value ignores double clicks
		// and prevents multiple windows from opening - issue in Firefox
		noDblClick : 600, // ms
		lastEvent  : 0,
		// prevent overlapping multiple opens in case rendering of content in
		// popup or download is longer than noDblClick time.
		busy       : false,

		// wrap line breaks & tabs in quotes
		regexQuote : /([\n\t\x09\x0d\x0a]|<[^<]+>)/, // test if cell needs wrapping quotes
		regexBR    : /(<br([\s\/])?>|\n)/g, // replace
		regexIMG   : /<img[^>]+alt\s*=\s*['"]([^'"]+)['"][^>]*>/i, // match
		regexHTML  : /<[^<]+>/g, // replace

		replaceCR  : '\x0d\x0a',
		replaceTab : '\x09',

		popupTitle : 'Output',
		popupStyle : 'width:100%;height:100%;margin:0;resize:none;', // for textarea
		message    : 'Your device does not support downloading. Please try again in desktop browser.',

		init : function(c) {
			c.$table
				.off(output.event)
				.on(output.event, function( e ) {
					e.stopPropagation();
					// prevent multiple windows opening
					if (
						!output.busy &&
						(e.timeStamp - output.lastEvent > output.noDblClick)
					) {
						output.lastEvent = e.timeStamp;
						output.busy = true;
						// explicitly use table.config.widgetOptions because we want
						// the most up-to-date values; not the 'wo' from initialization
						output.process(c, c.widgetOptions);
					}
				});
		},

		processRow: function(c, $rows, isHeader, isJSON) {
			var $cell, $cells, cellsLen, rowIndex, row, col, indx, rowspanLen, colspanLen, txt,
				wo = c.widgetOptions,
				tmpRow = [],
				dupe = wo.output_duplicateSpans,
				addSpanIndex = isHeader && isJSON && wo.output_headerRows && $.isFunction(wo.output_callbackJSON),
				cellIndex = 0,
				rowsLength = $rows.length;

			for ( rowIndex = 0; rowIndex < rowsLength; rowIndex++ ) {
				if (!tmpRow[rowIndex]) { tmpRow[rowIndex] = []; }
				cellIndex = 0;
				$cells = $rows.eq( rowIndex ).children();
				cellsLen = $cells.length;
				for ( indx = 0; indx < cellsLen; indx++ ) {
					$cell = $cells.eq( indx );
					// process rowspans
					if ($cell.filter('[rowspan]').length) {
						rowspanLen = parseInt( $cell.attr('rowspan'), 10) - 1;
						txt = output.formatData( c, wo, $cell, isHeader, indx );
						for (row = 1; row <= rowspanLen; row++) {
							if (!tmpRow[rowIndex + row]) { tmpRow[rowIndex + row] = []; }
							tmpRow[rowIndex + row][cellIndex] = isHeader ? txt : dupe ? txt : '';
						}
					}
					// process colspans
					if ($cell.filter('[colspan]').length) {
						colspanLen = parseInt( $cell.attr('colspan'), 10) - 1;
						// allow data-attribute to be an empty string
						txt = output.formatData( c, wo, $cell, isHeader, indx );
						for (col = 0; col < colspanLen; col++) {
							// if we're processing the header & making JSON, the header names need to be unique
							if ($cell.filter('[rowspan]').length) {
								rowspanLen = parseInt( $cell.attr('rowspan'), 10);
								for (row = 0; row < rowspanLen; row++) {
									if (!tmpRow[rowIndex + row]) { tmpRow[rowIndex + row] = []; }
									tmpRow[rowIndex + row][cellIndex + col] = addSpanIndex ?
										wo.output_callbackJSON($cell, txt, cellIndex + col) ||
										txt + '(' + (cellIndex + col) + ')' : isHeader ? txt : dupe ? txt : '';
								}
							} else {
								tmpRow[rowIndex][cellIndex + col] = addSpanIndex ?
									wo.output_callbackJSON($cell, txt, cellIndex + col) ||
									txt + '(' + (cellIndex + col) + ')' : isHeader ? txt : dupe ? txt : '';
							}
						}
					}

					// skip column if already defined
					while (typeof tmpRow[rowIndex][cellIndex] !== 'undefined') { cellIndex++; }

					tmpRow[rowIndex][cellIndex] = tmpRow[rowIndex][cellIndex] ||
						output.formatData( c, wo, $cell, isHeader, cellIndex );
					cellIndex++;
				}
			}
			return ts.output.removeColumns( c, wo, tmpRow );
		},

		// remove hidden/ignored columns
		removeColumns : function( c, wo, arry ) {
			var rowIndex, row, colIndex,
				data = [],
				len = arry.length;
			for ( rowIndex = 0; rowIndex < len; rowIndex++ ) {
				row = arry[ rowIndex ];
				data[ rowIndex ] = [];
				for ( colIndex = 0; colIndex < c.columns; colIndex++ ) {
					if ( !wo.output_hiddenColumnArray[ colIndex ] ) {
						data[ rowIndex ].push( row[ colIndex ] );
					}
				}
			}
			return data;
		},

		// optional vars $rows and dump added by TheSin to make
		// process callable via callback for ajaxPager
		process : function(c, wo, $rows, dump) {
			var mydata, $this, headers, csvData, len, rowsLen, tmp,
				hasStringify = window.JSON && JSON.hasOwnProperty('stringify'),
				indx = 0,
				tmpData = (wo.output_separator || ',').toLowerCase(),
				outputJSON = tmpData === 'json',
				outputArray = tmpData === 'array',
				separator = outputJSON || outputArray ? ',' : wo.output_separator,
				saveRows = wo.output_saveRows,
				$el = c.$table;
			// regex to look for the set separator or HTML
			wo.output_regex = new RegExp('(' + (/\\/.test(separator) ? '\\' : '' ) + separator + ')' );

			// make a list of hidden columns
			wo.output_hiddenColumnArray = [];
			for ( indx = 0; indx < c.columns; indx++ ) {
				wo.output_hiddenColumnArray[ indx ] = $.inArray( indx, wo.output_ignoreColumns ) > -1 ||
				( !wo.output_hiddenColumns && c.$headerIndexed[ indx ].css( 'display' ) === 'none' &&
					!c.$headerIndexed[ indx ].hasClass( 'tablesorter-scroller-hidden-column' )  );
			}

			// get header cells
			$this = $el
				.children('thead').children('tr')
				.not('.' + (ts.css.filterRow || 'tablesorter-filter-row') )
				.filter( function() {
					return wo.output_hiddenColumns || $(this).css('display') !== 'none';
				});
			headers = output.processRow(c, $this, true, outputJSON);

			// all tbody rows - do not include widget added rows (e.g. grouping widget headers)
			if ( !$rows ) {
				$rows = $el.children('tbody').children('tr').not(c.selectorRemove);
			}

			// check for a filter callback function first! because
			// /^f/.test(function() { console.log('test'); }) is TRUE! (function is converted to a string)
			$rows = typeof saveRows === 'function' ? $rows.filter(saveRows) :
				// get (f)iltered, (v)isible, all rows (look for the first letter only), or jQuery filter selector
				/^f/.test(saveRows) ? $rows.not('.' + (wo.filter_filteredRow || 'filtered') ) :
				/^v/.test(saveRows) ? $rows.filter(':visible') :
				// look for '.' (class selector), '#' (id selector),
				// ':' (basic filters, e.g. ':not()') or '[' (attribute selector start)
				/^[.#:\[]/.test(saveRows) ? $rows.filter(saveRows) :
				// default to all rows
				$rows;

			// process to array of arrays
			csvData = output.processRow(c, $rows);
			if (wo.output_includeFooter) {
				// clone, to force the tfoot rows to the end of this selection of rows
				// otherwise they appear after the thead (the order in the HTML)
				csvData = csvData.concat( output.processRow( c, $el.children('tfoot').children('tr:visible') ) );
			}

			len = headers.length;

			if (outputJSON) {
				tmpData = [];
				rowsLen = csvData.length;
				for ( indx = 0; indx < rowsLen; indx++ ) {
					// multiple header rows & output_headerRows = true, pick the last row...
					tmp = headers[ ( len > 1 && wo.output_headerRows ) ? indx % len : len - 1 ];
					tmpData.push( output.row2Hash( tmp, csvData[ indx ] ) );
				}

				// requires JSON stringify; if it doesn't exist, the output will show [object Object],... in the output window
				mydata = hasStringify ? JSON.stringify(tmpData) : tmpData;
			} else {
				if (wo.output_includeHeader) {
					tmp = [ headers[ ( len > 1 && wo.output_headerRows ) ? indx % len : len - 1 ] ];
					tmpData = output.row2CSV(wo, wo.output_headerRows ? headers : tmp, outputArray)
						.concat( output.row2CSV(wo, csvData, outputArray) );
				} else {
					tmpData = output.row2CSV(wo, csvData, outputArray);
				}

				// stringify the array; if stringify doesn't exist the array will be flattened
				mydata = outputArray && hasStringify ? JSON.stringify(tmpData) : tmpData.join('\n');
			}

			if (dump) {
				return mydata;
			}

			// callback; if true returned, continue processing
			if ($.isFunction(wo.output_callback)) {
				tmp = wo.output_callback(c, mydata, c.pager && c.pager.ajaxObject.url || null);
				if ( tmp === false ) {
					output.busy = false;
					return;
				} else if ( typeof tmp === 'string' ) {
					mydata = tmp;
				}
			}

			if ( /p/i.test( wo.output_delivery || '' ) ) {
				output.popup(mydata, wo.output_popupStyle, outputJSON || outputArray);
			} else {
				output.download(c, wo, mydata);
			}
			output.busy = false;

		}, // end process

		row2CSV : function(wo, tmpRow, outputArray) {
			var tmp, rowIndex,
				csvData = [],
				rowLen = tmpRow.length;
			for (rowIndex = 0; rowIndex < rowLen; rowIndex++) {
				// remove any blank rows
				tmp = ( tmpRow[rowIndex] || [] ).join('').replace(/\"/g, '');
				if ( ( tmpRow[rowIndex] || [] ).length > 0 && tmp !== '' ) {
					csvData[csvData.length] = outputArray ? tmpRow[rowIndex] : tmpRow[rowIndex].join(wo.output_separator);
				}
			}
			return csvData;
		},

		row2Hash : function( keys, values ) {
			var indx,
				json = {},
				len = values.length;
			for ( indx = 0; indx < len; indx++ ) {
				if ( indx < keys.length ) {
					json[ keys[ indx ] ] = values[ indx ];
				}
			}
			return json;
		},

		formatData : function(c, wo, $el, isHeader, colIndex) {
			var attr = $el.attr(wo.output_dataAttrib),
				txt = typeof attr !== 'undefined' ? attr : $el.html(),
				quotes = (wo.output_separator || ',').toLowerCase(),
				separator = quotes === 'json' || quotes === 'array',
				// replace " with “ if undefined
				result = txt.replace(/\"/g, wo.output_replaceQuote || '\u201c');
			// replace line breaks with \\n & tabs with \\t
			if (!wo.output_trimSpaces) {
				result = result.replace(output.regexBR, output.replaceCR).replace(/\t/g, output.replaceTab);
			} else {
				result = result.replace(output.regexBR, '');
			}
			// extract img alt text
			txt = result.match(output.regexIMG);
			if (!wo.output_includeHTML && txt !== null) {
				result = txt[1];
			}
			// replace/remove html
			result = wo.output_includeHTML && !isHeader ? result : result.replace(output.regexHTML, '');
			result = wo.output_trimSpaces || isHeader ? $.trim(result) : result;
			// JSON & array outputs don't need quotes
			quotes = separator ? false : wo.output_wrapQuotes || wo.output_regex.test(result) || output.regexQuote.test(result);
			result = quotes ? '"' + result + '"' : result;
			// formatting callback - added v2.22.4
			if ( typeof wo.output_formatContent === 'function' ) {
				return wo.output_formatContent( c, wo, {
					isHeader : isHeader || false,
					$cell : $el,
					content : result,
					columnIndex: colIndex,
					parsed: c.parsers[colIndex].format(result, c.table, $el[0], colIndex)
				});
			}

			return result;
		},

		popup : function(data, style, wrap) {
			var generator = window.open('', output.popupTitle, style);
			try {
				generator.document.write(
					'<html><head><title>' + output.popupTitle + '</title></head><body>' +
					'<textarea wrap="' + (wrap ? 'on' : 'off') + '" style="' +
					output.popupStyle + '">' + data + '\n</textarea>' +
					'</body></html>'
				);
				generator.document.close();
				generator.focus();
			} catch (e) {
				// popup already open
				generator.close();
				return output.popup(data, style, wrap);
			}
			// select all text and focus within the textarea in the popup
			// $(generator.document).find('textarea').select().focus();
			return true;
		},

		// modified from https://github.com/PixelsCommander/Download-File-JS
		// & http://html5-demos.appspot.com/static/a.download.html
		download : function (c, wo, data) {

			if (typeof wo.output_savePlugin === 'function') {
				return wo.output_savePlugin(c, wo, data);
			}

			var e, blob, gotBlob, bom,
				nav = window.navigator,
				link = document.createElement('a');

			// iOS devices do not support downloading. We have to inform user about
			// this limitation.
			if (/(iP)/g.test(nav.userAgent)) {
				alert(output.message);
				return false;
			}

			// test for blob support
			try {
				gotBlob = !!new Blob();
			} catch (err) {
				gotBlob = false;
			}

			// Use HTML5 Blob if browser supports it
			if ( gotBlob ) {

				window.URL = window.URL || window.webkitURL;
				// prepend BOM for UTF-8 XML and text/* types (including HTML)
				// note: your browser will automatically convert UTF-16 U+FEFF to EF BB BF
				// see https://github.com/eligrey/FileSaver.js/blob/master/FileSaver.js#L68
				bom = (/^\s*(?:text\/\S*|application\/xml|\S*\/\S*\+xml)\s*;.*charset\s*=\s*utf-8/i.test(wo.output_encoding)) ?
					[ '\ufeff', data ] : [ data ];
				blob = new Blob( bom, { type: wo.output_encoding } );

				if (nav.msSaveBlob) {
					// IE 10+
					nav.msSaveBlob(blob, wo.output_saveFileName);
				} else {
					// all other browsers
					link.href = window.URL.createObjectURL(blob);
					link.download = wo.output_saveFileName;
					// Dispatching click event; using $(link).trigger() won't work
					if (document.createEvent) {
						e = document.createEvent('MouseEvents');
						// event.initMouseEvent(type, canBubble, cancelable, view, detail, screenX, screenY, clientX, clientY,
						// ctrlKey, altKey, shiftKey, metaKey, button, relatedTarget);
						e.initMouseEvent('click', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
						link.dispatchEvent(e);
					}
				}
				return false;
			}

			// fallback to force file download (whether supported by server).
			// not sure if this actually works in IE9 and older...
			window.open( wo.output_encoding + encodeURIComponent(data) + '?download', '_self');
			return true;

		},

		remove : function(c) {
			c.$table.off(output.event);
		}

	};

	ts.addWidget({
		id: 'output',
		options: {
			output_separator      : ',',         // set to 'json', 'array' or any separator
			output_ignoreColumns  : [],          // columns to ignore [0, 1,... ] (zero-based index)
			output_hiddenColumns  : false,       // include hidden columns in the output
			output_includeFooter  : false,       // include footer rows in the output
			output_includeHeader  : true,        // include header rows in the output
			output_headerRows     : false,       // if true, include multiple header rows
			output_dataAttrib     : 'data-name', // header attrib containing modified header name
			output_delivery       : 'popup',     // popup, download
			output_saveRows       : 'filtered',  // (a)ll, (v)isible, (f)iltered or jQuery filter selector
			output_duplicateSpans : true,        // duplicate output data in tbody colspan/rowspan
			output_replaceQuote   : '\u201c;',   // left double quote
			output_includeHTML    : false,
			output_trimSpaces     : true,
			output_wrapQuotes     : false,
			output_popupStyle     : 'width=500,height=300',
			output_saveFileName   : 'mytable.csv',
			// format $cell content callback
			output_formatContent  : null, // function(config, widgetOptions, data) { return data.content; }
			// callback executed when processing completes
			// return true to continue download/output
			// return false to stop delivery & do something else with the data
			output_callback      : function(/* config, data */) { return true; },
			// JSON callback executed when a colspan is encountered in the header
			output_callbackJSON  : function($cell, txt, cellIndex) { return txt + '(' + (cellIndex) + ')'; },
			// the need to modify this for Excel no longer exists
			output_encoding      : 'data:application/octet-stream;charset=utf8,',
			// override internal save file code and use an external plugin such as
			// https://github.com/eligrey/FileSaver.js
			output_savePlugin    : null /* function(c, wo, data) {
				var blob = new Blob([data], {type: wo.output_encoding});
				saveAs(blob, wo.output_saveFileName);
			} */
		},
		init: function(table, thisWidget, c) {
			output.init(c);
		},
		remove: function(table, c) {
			output.remove(c);
		}

	});

})(jQuery);
