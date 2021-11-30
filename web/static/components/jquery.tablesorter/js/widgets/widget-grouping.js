/*! Widget: grouping - updated 9/27/2017 (v2.29.0) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * by Rob Garrison
 */
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery: false */
;(function($) {
	'use strict';
	var ts = $.tablesorter,

	tsg = ts.grouping = {

		types : {
			number : function(c, $column, txt, num) {
				var result,
					ascSort = $column.hasClass( ts.css.sortAsc );
				if ( num > 1 && txt !== '' ) {
					if ( ascSort ) {
						result = Math.floor( parseFloat( txt ) / num ) * num;
					} else {
						result = Math.ceil( parseFloat( txt ) / num ) * num;
					}
					// show range
					result += ' - ' + ( result + ( num - 1 ) * ( ascSort ? 1 : -1 ) );
				} else {
					result = parseFloat( txt ) || txt;
				}
				return result;
			},
			separator : function(c, $column, txt, num) {
				var word = (txt + '').split(c.widgetOptions.group_separator);
				// return $.trim(word && num > 0 && word.length >= num ? word[(num || 1) - 1] : '');
				return $.trim( word[ num - 1 ] || '' );
			},
			text : function( c, $column, txt ) {
				return txt;
			},
			word : function(c, $column, txt, num) {
				var word = (txt + ' ').match(/\w+/g) || [];
				// return word && word.length >= num ? word[num - 1] : txt || '';
				return word[ num - 1 ] || '';
			},
			letter : function(c, $column, txt, num) {
				return txt ? (txt + ' ').substring(0, num) : '';
			},
			date : function(c, $column, txt, part) {
				var year, month,
					wo = c.widgetOptions,
					time = new Date(txt || '');
				// check for valid date
				if ( time instanceof Date && isFinite( time ) ) {
					year = time.getFullYear();
					month = tsg.findMonth( wo, time.getMonth() );
					return part === 'year' ? year :
						part === 'month' ? month :
						part === 'monthyear' ?  month + ' ' + year :
						part === 'day' ? month + ' ' + time.getDate() :
						part === 'week' ? tsg.findWeek( wo, time.getDay() ) :
						part === 'time' ? tsg.findTime( wo, time ) :
						part === 'hour' ? tsg.findTime( wo, time, 'hour' ) :
						wo.group_dateString( time, c, $column );
				} else {
					return wo.group_dateInvalid;
				}
			}
		},

		// group date type functions to allow using this widget with Globalize
		findMonth : function( wo, month ) {
			// CLDR returns an object { 1: "Jan", 2: "Feb", 3: "Mar", ..., 12: "Dec" }
			return wo.group_months[ month + ( ( wo.group_months[0] || '' ) === '' ? 1 : 0 ) ];
		},
		findWeek : function( wo, day ) {
			if ( $.isArray( wo.group_week ) ) {
				return wo.group_week[ day ];
			} else if ( !$.isEmptyObject( wo.group_week ) ) {
				// CLDR returns { sun: "Sun", mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", ... }
				var cldrWeek = [ 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat' ];
				return wo.group_week[ cldrWeek[ day ] ];
			}
		},
		findTime : function( wo, time, part ) {
			var suffix,
				// CLDR returns { am: "AM", pm: "PM", ... }
				isObj = wo.group_time.am && wo.group_time.pm,
				h = time.getHours(),
				period = h >= 12 ? 1 : 0,
				p24 = wo.group_time24Hour && h > 12 ? h - 12 :
					wo.group_time24Hour && h === 0 ? h + 12 : h,
				hours = ( '00' + p24 ).slice(-2),
				min = ( '00' + time.getMinutes() ).slice(-2);
			suffix = wo.group_time[ isObj ? [ 'am', 'pm' ][ period ] : period ];
			if ( part === 'hour' ) {
				return hours;
			}
			return hours + ':' + min + ( wo.group_time24Hour ? '' : ' ' + ( suffix || '' ) );
		},

		update : function(table) {
			if ($.isEmptyObject(table.config.cache)) { return; }
			var c = table.config,
				wo = c.widgetOptions,
				hasSort = typeof c.sortList[0] !== 'undefined',
				data = {},
				column = $.isArray( wo.group_forceColumn ) && typeof wo.group_forceColumn[0] !== 'undefined' ?
					( wo.group_enforceSort && !hasSort ? -1 : wo.group_forceColumn[0] ) :
					( hasSort ? c.sortList[0][0] : -1 );
			c.$table
				.find('tr.group-hidden').removeClass('group-hidden').end()
				.find('tr.group-header').remove();
			if (wo.group_collapsible) {
				// clear pager saved spacer height (in case the rows are collapsed)
				c.$table.data('pagerSavedHeight', 0);
			}
			if (column >= 0 && column < c.columns && !c.$headerIndexed[column].hasClass('group-false')) {
				wo.group_collapsedGroup = ''; // save current groups
				wo.group_collapsedGroups = {};

				data.column = column;
				// group class finds 'group-{word/separator/letter/number/date/false}-{optional:#/year/month/day/week/time}'
				data.groupClass = (c.$headerIndexed[column].attr('class') || '').match(/(group-\w+(-\w+)?)/g);
				// grouping = [ 'group', '{word/separator/letter/number/date/false}', '{#/year/month/day/week/time}' ]
				data.grouping = data.groupClass ? data.groupClass[0].split('-') : [ 'group', 'letter', 1 ]; // default to letter 1

				// save current grouping
				data.savedGroup = tsg.saveCurrentGrouping( c, wo, data );

				// find column groups
				tsg.findColumnGroups( c, wo, data );
				tsg.processHeaders( c, wo, data );

				c.$table.triggerHandler(wo.group_complete);
			}
		},

		processHeaders : function( c, wo, data ) {
			var index, isHidden, $label, name, $rows, $row,
				$headers = c.$table.find( 'tr.group-header' ),
				len = $headers.length;

			$headers.bind( 'selectstart', false );
			for ( index = 0; index < len; index++ ) {
				$row = $headers.eq( index );
				$rows = $row.nextUntil( 'tr.group-header' ).filter( ':visible' );

				// add group count (only visible rows!)
				if ( wo.group_count || $.isFunction( wo.group_callback ) ) {
					$label = $row.find( '.group-count' );
					if ( $label.length ) {
						if ( wo.group_count ) {
							$label.html( wo.group_count.toString().replace( /\{num\}/g, $rows.length ) );
						}
						if ( $.isFunction( wo.group_callback ) ) {
							wo.group_callback( $row.find( 'td' ), $rows, data.column, c.table );
						}
					}
				}
				// save collapsed groups
				if ( wo.group_saveGroups &&
					!$.isEmptyObject( wo.group_collapsedGroups ) &&
					wo.group_collapsedGroups[ wo.group_collapsedGroup ].length ) {
					name = $row.find( '.group-name' ).text().toLowerCase() + $row.attr( 'data-group-index' );
					isHidden = $.inArray( name, wo.group_collapsedGroups[ wo.group_collapsedGroup ] ) > -1;
					$row.toggleClass( 'collapsed', isHidden );
					$rows.toggleClass( 'group-hidden', isHidden );
				} else if ( wo.group_collapsed && wo.group_collapsible ) {
					$row.addClass( 'collapsed' );
					$rows.addClass( 'group-hidden' );
				}
			}
		},

		groupHeaderHTML : function( c, wo, data ) {
			var name = ( data.currentGroup || '' ).toString().replace(/</g, '&lt;').replace(/>/g, '&gt;');
			return '<tr class="group-header ' + c.selectorRemove.slice(1) + ' ' +
				// prevent grouping row from being hidden by the columnSelector;
				// classHasSpan option added 2.29.0
				( wo.columnSelector_classHasSpan || 'hasSpan' ) +
				'" unselectable="on" ' + ( c.tabIndex ? 'tabindex="0" ' : '' ) + 'data-group-index="' +
				data.groupIndex + '">' +
				'<td colspan="' + c.columns + '">' +
					( wo.group_collapsible ? '<i/>' : '' ) +
					'<span class="group-name">' + name + '</span>' +
					'<span class="group-count"></span>' +
				'</td></tr>';
		},
		saveCurrentGrouping : function( c, wo, data ) {
			// save current grouping
			var saveName, direction,
				savedGroup = false;
			if (wo.group_collapsible && wo.group_saveGroups) {
				wo.group_collapsedGroups = ts.storage && ts.storage( c.table, 'tablesorter-groups' ) || {};
				// include direction when saving groups (reversed numbers shows different range values)
				direction = 'dir' + c.sortList[0][1];
				// combine column, sort direction & grouping as save key
				saveName = wo.group_collapsedGroup = '' + c.sortList[0][0] + direction + data.grouping.join('');
				if (!wo.group_collapsedGroups[saveName]) {
					wo.group_collapsedGroups[saveName] = [];
				} else {
					savedGroup = true;
				}
			}
			return savedGroup;
		},
		findColumnGroups : function( c, wo, data ) {
			var tbodyIndex, norm_rows, rowIndex, end, undef,
				hasPager = ts.hasWidget( c.table, 'pager' ),
				p = c.pager || {};
			data.groupIndex = 0;
			for ( tbodyIndex = 0; tbodyIndex < c.$tbodies.length; tbodyIndex++ ) {
				norm_rows = c.cache[ tbodyIndex ].normalized;
				data.group = undef; // clear grouping across tbodies
				rowIndex = hasPager && !p.ajax ? p.startRow - 1 : 0;
				end = hasPager ? p.endRow - ( p.ajax ? p.startRow : 0 ) : norm_rows.length;
				for ( ; rowIndex < end; rowIndex++ ) {
					data.rowData = norm_rows[ rowIndex ];
					// fixes #1232 - ajax issue; if endRow > norm_rows.length (after filtering), then data.rowData is undefined
					if (data.rowData) {
						data.$row = data.rowData[ c.columns ].$row;
						// fixes #438
						if ( data.$row.is( ':visible' ) && tsg.types[ data.grouping[ 1 ] ] ) {
							tsg.insertGroupHeader( c, wo, data );
						}
					}
				}
			}
			if ( ts.hasWidget( c.table, 'columnSelector' ) ) {
				// make sure to handle the colspan adjustments of the grouping rows
				ts.columnSelector.setUpColspan( c, wo );
			}
		},
		insertGroupHeader: function( c, wo, data ) {
			var $header = c.$headerIndexed[ data.column ],
				txt = data.rowData[ data.column ],
				num = /date/.test( data.groupClass ) ? data.grouping[ 2 ] : parseInt( data.grouping[ 2 ] || 1, 10 ) || 1;
			data.currentGroup = data.rowData ?
				tsg.types[ data.grouping[ 1 ] ]( c, $header, txt, num, data.group ) :
				data.currentGroup;
			if ( data.group !== data.currentGroup ) {
				data.group = data.currentGroup;
				if ( $.isFunction( wo.group_formatter ) ) {
					data.currentGroup = wo.group_formatter( ( data.group || '' ).toString(), data.column, c.table, c, wo, data ) || data.group;
				}
				// add first() for grouping with childRows
				data.$row.first().before( tsg.groupHeaderHTML( c, wo, data ) );
				if ( wo.group_saveGroups && !data.savedGroup && wo.group_collapsed && wo.group_collapsible ) {
					// all groups start collapsed; data.groupIndex is 1 more than the expected index.
					wo.group_collapsedGroups[ wo.group_collapsedGroup ].push( data.currentGroup + data.groupIndex );
				}
				data.groupIndex++;
			}
		},

		bindEvents : function(table, c, wo) {
			if (wo.group_collapsible) {
				wo.group_collapsedGroups = [];
				// .on() requires jQuery 1.7+
				c.$table.on('click toggleGroup keyup', 'tr.group-header', function(event) {
					event.stopPropagation();
					// pressing enter will toggle the group
					if (event.type === 'keyup' && event.which !== 13) { return; }
					var isCollapsed, indx,
						$this = $(this),
						name = $this.find('.group-name').text().toLowerCase() + $this.attr('data-group-index');
					// use shift-click to toggle ALL groups
					if (event.shiftKey && (event.type === 'click' || event.type === 'keyup')) {
						$this.siblings('.group-header').trigger('toggleGroup');
					}
					$this.toggleClass('collapsed');
					// nextUntil requires jQuery 1.4+
					$this.nextUntil('tr.group-header').toggleClass('group-hidden', $this.hasClass('collapsed') );
					isCollapsed = $this.hasClass('collapsed');
					// reapply zebra widget after opening collapsed group - see #1156
					if (!isCollapsed && ts.hasWidget(c.$table, 'zebra')) {
						ts.applyWidgetId(c.$table, 'zebra');
					}
					// save collapsed groups
					if (wo.group_saveGroups && ts.storage) {
						if (!wo.group_collapsedGroups[wo.group_collapsedGroup]) {
							wo.group_collapsedGroups[wo.group_collapsedGroup] = [];
						}
						if (isCollapsed && wo.group_collapsedGroup) {
							wo.group_collapsedGroups[wo.group_collapsedGroup].push( name );
						} else if (wo.group_collapsedGroup) {
							indx = $.inArray( name, wo.group_collapsedGroups[wo.group_collapsedGroup]  );
							if (indx > -1) {
								wo.group_collapsedGroups[wo.group_collapsedGroup].splice( indx, 1 );
							}
						}
						ts.storage( table, 'tablesorter-groups', wo.group_collapsedGroups );
					}
				});
			}
			$(wo.group_saveReset).on('click', function() {
				tsg.clearSavedGroups(table);
			});
			c.$table.on('pagerChange.tsgrouping', function() {
				tsg.update(table);
			});
		},

		clearSavedGroups: function(table) {
			if (table && ts.storage) {
				ts.storage(table, 'tablesorter-groups', '');
				tsg.update(table);
			}
		}

	};

	ts.addWidget({
		id: 'group',
		priority: 100,
		options: {
			group_collapsible : true, // make the group header clickable and collapse the rows below it.
			group_collapsed   : false, // start with all groups collapsed
			group_saveGroups  : true, // remember collapsed groups
			group_saveReset   : null, // element to clear saved collapsed groups
			group_count       : ' ({num})', // if not false, the '{num}' string is replaced with the number of rows in the group
			group_separator   : '-',  // group name separator; used when group-separator-# class is used.
			group_formatter   : null, // function(txt, column, table, c, wo) { return txt; }
			group_callback    : null, // function($cell, $rows, column, table) {}, callback allowing modification of the group header labels
			group_complete    : 'groupingComplete', // event triggered on the table when the grouping widget has finished work

			// apply the grouping widget only to selected column
			group_forceColumn : [],   // only the first value is used; set as an array for future expansion
			group_enforceSort : true, // only apply group_forceColumn when a sort is applied to the table

			// checkbox parser text used for checked/unchecked values
			group_checkbox    : [ 'checked', 'unchecked' ],
			// change these default date names based on your language preferences
			group_months      : [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ],
			group_week        : [ 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday' ],
			group_time        : [ 'AM', 'PM' ],

			// use 12 vs 24 hour time
			group_time24Hour  : false,
			// group header text added for invalid dates
			group_dateInvalid : 'Invalid Date',

			// this function is used when 'group-date' is set to create the date string
			// you can just return date, date.toLocaleString(), date.toLocaleDateString() or d.toLocaleTimeString()
			// reference: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date#Conversion_getter
			group_dateString  : function(date) { return date.toLocaleString(); }
		},
		init: function(table, thisWidget, c, wo) {
			tsg.bindEvents(table, c, wo);
		},
		format: function(table) {
			tsg.update(table);
		},
		remove : function(table, c) {
			c.$table
				.off('click', 'tr.group-header')
				.off('pagerChange.tsgrouping')
				.find('.group-hidden').removeClass('group-hidden').end()
				.find('tr.group-header').remove();
		}
	});

})(jQuery);
