/*! Widget: saveSort - updated 2018-03-19 (v2.30.1) *//*
* Requires tablesorter v2.16+
* by Rob Garrison
*/
;(function ($) {
	'use strict';
	var ts = $.tablesorter || {};

	function getStoredSortList(c) {
		var stored = ts.storage( c.table, 'tablesorter-savesort' );
		return (stored && stored.hasOwnProperty('sortList') && $.isArray(stored.sortList)) ? stored.sortList : [];
	}

	function sortListChanged(c, sortList) {
		return (sortList || getStoredSortList(c)).join(',') !== c.sortList.join(',');
	}

	// this widget saves the last sort only if the
	// saveSort widget option is true AND the
	// $.tablesorter.storage function is included
	// **************************
	ts.addWidget({
		id: 'saveSort',
		priority: 20,
		options: {
			saveSort : true
		},
		init: function(table, thisWidget, c, wo) {
			// run widget format before all other widgets are applied to the table
			thisWidget.format(table, c, wo, true);
		},
		format: function(table, c, wo, init) {
			var time,
				$table = c.$table,
				saveSort = wo.saveSort !== false, // make saveSort active/inactive; default to true
				sortList = { 'sortList' : c.sortList },
				debug = ts.debug(c, 'saveSort');
			if (debug) {
				time = new Date();
			}
			if ($table.hasClass('hasSaveSort')) {
				if (saveSort && table.hasInitialized && ts.storage && sortListChanged(c)) {
					ts.storage( table, 'tablesorter-savesort', sortList );
					if (debug) {
						console.log('saveSort >> Saving last sort: ' + c.sortList + ts.benchmark(time));
					}
				}
			} else {
				// set table sort on initial run of the widget
				$table.addClass('hasSaveSort');
				sortList = '';
				// get data
				if (ts.storage) {
					sortList = getStoredSortList(c);
					if (debug) {
						console.log('saveSort >> Last sort loaded: "' + sortList + '"' + ts.benchmark(time));
					}
					$table.bind('saveSortReset', function(event) {
						event.stopPropagation();
						ts.storage( table, 'tablesorter-savesort', '' );
					});
				}
				// init is true when widget init is run, this will run this widget before all other widgets have initialized
				// this method allows using this widget in the original tablesorter plugin; but then it will run all widgets twice.
				if (init && sortList && sortList.length > 0) {
					c.sortList = sortList;
				} else if (table.hasInitialized && sortList && sortList.length > 0) {
					// update sort change
					if (sortListChanged(c, sortList)) {
						ts.sortOn(c, sortList);
					}
				}
			}
		},
		remove: function(table, c) {
			c.$table.removeClass('hasSaveSort');
			// clear storage
			if (ts.storage) { ts.storage( table, 'tablesorter-savesort', '' ); }
		}
	});

})(jQuery);
