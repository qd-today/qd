/*! Widget: filter, select2 formatter function - updated 12/1/2019 (v2.31.2) *//*
 * requires: jQuery 1.7.2+, tableSorter (FORK) 2.16+, filter widget 2.16+
 and select2 v3.4.6+ plugin (this code is NOT compatible with select2 v4+)
 */
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery: false */
;(function($) {
	'use strict';

	var ts = $.tablesorter || {};
	ts.filterFormatter = ts.filterFormatter || {};

	/************************\
	 Select2 Filter Formatter
	\************************/
	ts.filterFormatter.select2 = function($cell, indx, select2Def) {
		var o = $.extend({
			// select2 filter formatter options
			cellText : '', // Text (wrapped in a label element)
			match : true, // adds 'filter-match' to header
			value : '',
			// include ANY select2 options below
			multiple : true,
			width : '100%'

		}, select2Def ),
		arry, data,
		// add class to $cell since it may point to a removed DOM node
		// after a "refreshWidgets"; see #1237
		c = $cell.addClass('select2col' + indx).closest('table')[0].config,
		wo = c.widgetOptions,
		// Add a hidden input to hold the range values
		$input = $('<input class="filter" type="hidden">')
			.appendTo($cell)
			// hidden filter update namespace trigger by filter widget
			.bind('change' + c.namespace + 'filter', function() {
				var val = convertRegex(this.value);
				c.$table.find('.select2col' + indx + ' .select2').select2('val', val);
				updateSelect2();
			}),
		$header = c.$headerIndexed[indx],
		onlyAvail = $header.hasClass(wo.filter_onlyAvail),
		matchPrefix = o.match ? '' : '^',
		matchSuffix = o.match ? '' : '$',
		flags = wo.filter_ignoreCase ? 'i' : '',

		convertRegex = function(val) {
			// value = '/(^x$|^y$)/' => ['x','y']
			return val
				.replace(/^\/\(\^?/, '')
				.replace(/\$\|\^/g, '|')
				.replace(/\$?\)\/i?$/g, '')
				// unescape special regex characters
				.replace(/\\/g, '')
				.split('|');
		},

		// this function updates the hidden input and adds the current values to the header cell text
		updateSelect2 = function() {
			var arry = false,
				v = c.$table.find('.select2col' + indx + ' .select2').select2('val') || o.value || '';
			// convert array to string
			if ($.isArray(v)) {
				arry = true;
				v = v.join('\u0000');
			}
			// escape special regex characters (http://stackoverflow.com/a/9310752/145346)
			var v_escape = v.replace(/[-[\]{}()*+?.,/\\^$|#]/g, '\\$&');
			// convert string back into an array
			if (arry) {
				v = v.split('\u0000');
				v_escape =  v_escape.split('\u0000');
			}
			if (!ts.isEmptyObject($cell.find('.select2').data())) {
				$input
					// add regex, so we filter exact numbers
					.val(
						$.isArray(v_escape) && v_escape.length && v_escape.join('') !== '' ?
							'/(' + matchPrefix + (v_escape || []).join(matchSuffix + '|' + matchPrefix) + matchSuffix + ')/' + flags :
							''
					)
					.trigger('search');
				$cell.find('.select2').select2('val', v);
				// update sticky header cell
				if (c.widgetOptions.$sticky) {
					c.widgetOptions.$sticky.find('.select2col' + indx + ' .select2').select2('val', v);
				}
			}
		},

		// get options from table cell content or filter_selectSource (v2.16)
		updateOptions = function() {
			data = [];
			arry = ts.filter.getOptionSource(c.$table[0], indx, onlyAvail) || [];
			// build select2 data option
			$.each(arry, function(i, v) {
				// getOptionSource returns { parsed: "value", text: "value" } in v2.24.4
				data.push({ id: '' + v.parsed, text: v.text });
			});
			o.data = data;
		};

		// get filter-match class from option
		$header.toggleClass('filter-match', o.match);
		if (o.cellText) {
			$cell.prepend('<label>' + o.cellText + '</label>');
		}

		// don't add default in table options if either ajax or
		// data options are already defined
		if (!(o.ajax && !$.isEmptyObject(o.ajax)) && !o.data) {
			updateOptions();
			c.$table.bind('filterEnd', function() {
				updateOptions();
				c.$table
					.find('.select2col' + indx)
					.add(c.widgetOptions.$sticky && c.widgetOptions.$sticky.find('.select2col' + indx))
					.find('.select2').select2(o);
			});
		}

		// add a select2 hidden input!
		$('<input class="select2 select2-' + indx + '" type="hidden" />')
			.val(o.value)
			.appendTo($cell)
			.select2(o)
			.bind('change', function() {
				updateSelect2();
			});

		// update select2 from filter hidden input, in case of saved filters
		c.$table.bind('filterFomatterUpdate', function() {
			// value = '/(^x$|^y$)/' => 'x,y'
			var val = convertRegex(c.$table.data('lastSearch')[indx] || '');
			$cell = c.$table.find('.select2col' + indx);
			$cell.find('.select2').select2('val', val);
			updateSelect2();
			ts.filter.formatterUpdated($cell, indx);
		});

		// has sticky headers?
		c.$table.bind('stickyHeadersInit', function() {
			var $shcell = c.widgetOptions.$sticky.find('.select2col' + indx).empty();
			// add a select2!
			$('<input class="select2 select2-' + indx + '" type="hidden">')
				.val(o.value)
				.appendTo($shcell)
				.select2(o)
				.bind('change', function() {
					c.$table.find('.select2col' + indx)
						.find('.select2')
						.select2('val', c.widgetOptions.$sticky.find('.select2col' + indx + ' .select2').select2('val') );
					updateSelect2();
				});
			if (o.cellText) {
				$shcell.prepend('<label>' + o.cellText + '</label>');
			}
		});

		// on reset
		c.$table.bind('filterReset', function() {
			c.$table.find('.select2col' + indx).find('.select2').select2('val', o.value || '');
			setTimeout(function() {
				updateSelect2();
			}, 0);
		});

		updateSelect2();
		return $input;
	};

})(jQuery);
