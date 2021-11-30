/*! Widget: vertical-group (BETA) - updated 12/13/2017 (v2.29.1) */
/* Requires tablesorter and jQuery
 * Originally by @aavmurphy (Andrew Murphy)
 * Adapted for tablesorter by Rob Garrison - see #1469 & #1470
 *
 * This widget is licensed under the same terms at mottie/tablesorter itself, i.e. free to use
 */
/* jshint browser:true, jquery:true, unused:false */
/* global jQuery:false */
;(function($) {
	'use strict';

	var ts = $.tablesorter,
		tscss = ts.css;

	$.extend( ts.css, {
		verticalGroupHeader: 'tablesorter-vertical-group',
		verticalGroupHide:   'tablesorter-vertical-group-hide',
		verticalGroupShow:   'tablesorter-vertical-group-show'
	});

	ts.addWidget({
		id: 'vertical-group',
		priority: 99,
		init: verticalGroup,
		format: verticalGroup
	});

	function cleanUp( el ) {
		el.removeClass(tscss.verticalGroupHide + ' ' + tscss.verticalGroupShow);
	}

	function setZebra( wo, $cell, indx ) {
		var $row = $cell.parent();
		$row
			.removeClass( wo.zebra[ (indx + 1) % 2 ] )
			.addClass( wo.zebra[ indx % 2] );
	}

	function verticalGroup( table, c, wo ) {
		// -------------------------------------------------------------------------
		// loop thru the header row,
		//    - look for .vertical-group
		//
		// loop thru the rows
		//
		//    set ALWAYS_SHOW = FALSE
		//    loop thru the 1st 4 columns
		//      if this cell does not exist, skip to next row
		//      if ALWAYS_SHOW, then this cell is SHOW
		//      else if this column does not have '.vertical-group', then this cell is SHOW
		//      else if this cell is NOT the same as the cell-above, then this cell is SHOW
		//      else this cell is HIDE
		//      if this cell is SHOW, set ALWAYS_SHOW
		//      if this cell is SHOW,
		//      then
		//        set the cell class to .vertical_group_show
		//      else
		//        set the cell class to vertical_group_show
		//
		//      TO DO add/remove classes so as not to clobber other existing classes
		//      TO DO add classes
		//
		//        .vertical-group-show { background-color: white !important; }
		//        .vertical-group-hide { visibility: hidden; border-top: white !important;background-color: white !important; }
		//
		//        this is all because of stripped tables
		//          - background-colour show be the table's background colour (or the first row's)
		//          - the border-color needs to be the same
		//
		// ------------------------------------------------------------------------------------------------
		var zebra_index = -1, // increments at start of loop
			rows = table.tBodies[0].rows,
			has_zebra = ts.hasWidget( table, 'zebra'),
			is_vertical_group_col = [],
			last_row = [];

		if ( wo.vertical_group_lock ) {
			return;
		}
		wo.vertical_group_lock = true;

		is_vertical_group_col = $.map( c.$headerIndexed, function( el ) {
			return el.hasClass( tscss.verticalGroupHeader ) ? 1 : '';
		});

		if ( is_vertical_group_col.join('') === '' ) {
			cleanUp( $(rows).find( '.' + tscss.verticalGroupHide + ',.' + tscss.verticalGroupShow ) );
			wo.vertical_group_lock = false;
			return;
		}

		for (var i = 0; i < rows.length; i++) {
			var always_show_cell = false;

			for (var j = 0; j < c.columns; j++ ) {
				if ( !is_vertical_group_col[ j ] || !rows[ i ].cells[ j ] ) {
					zebra_index++;
					continue;
				}

				var $cell = $( rows[ i ].cells[ j ] ),
					// only group if column is sorted
					isSorted = ts.isValueInArray( j, c.sortList ), // returns equivalent of an indexOf value
					cell_data = $cell.html();

				if ( isSorted < 0 ) {
					cleanUp( $cell );
				} else if ( !always_show_cell && cell_data === last_row[j] ) {
					if ( !$cell.hasClass(tscss.verticalGroupHide) ) {
						$cell.addClass( tscss.verticalGroupHide );
					}
					if ( has_zebra ) {
						setZebra( wo, $cell, zebra_index );
					}
					$cell.removeClass( tscss.verticalGroupShow );
				} else if (isSorted === 0) {
					// only show cells from the first sorted column
					always_show_cell = true; // show
					if ( !$cell.hasClass( tscss.verticalGroupShow ) ) {
						$cell.addClass( tscss.verticalGroupShow );
					}
					$cell.removeClass( tscss.verticalGroupHide );
					if ( has_zebra ) {
						// only adjust striping based on the first sorted column
						setZebra( wo, $cell, isSorted ? zebra_index : ++zebra_index );
					}
				}
				last_row[j] = cell_data;
			}
		}
		wo.vertical_group_lock = false;
	}

})(jQuery);
