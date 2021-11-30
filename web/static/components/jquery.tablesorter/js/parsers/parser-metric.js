/*! Parser: metric *//*
 * Demo: http://jsfiddle.net/Mottie/abkNM/382/
 * Set the metric name in the header (defaults to 'm|meter'), e.g.
 *   <th data-metric-name-abbr="b|B" data-metric-name-full="byte|Byte|BYTE">HDD Size</th>
 *   <th data-metric-name="m|meter">Distance</th> <!-- data-metric-name is deprecated in v2.22.2 -->
 */
/*jshint jquery:true */
;( function( $ ) {
	'use strict';

	var prefixes = {
		// 'prefix' : [ base 10, base 2 ]
		// skipping IEEE 1541 defined prefixes: kibibyte, mebibyte, etc, for now.
		'Y|Yotta|yotta' : [ 1e24, Math.pow(1024, 8) ], // 1024^8
		'Z|Zetta|zetta' : [ 1e21, Math.pow(1024, 7) ], // 1024^7
		'E|Exa|exa'     : [ 1e18, Math.pow(1024, 6) ], // 1024^6
		'P|Peta|peta'   : [ 1e15, Math.pow(1024, 5) ], // 1024^5
		'T|Tera|tera'   : [ 1e12, Math.pow(1024, 4) ], // 1024^4
		'G|Giga|giga'   : [ 1e9,  Math.pow(1024, 3) ], // 1024^3
		'M|Mega|mega'   : [ 1e6,  Math.pow(1024, 2) ], // 1024^2
		'k|Kilo|kilo'   : [ 1e3, 1024 ], // 1024
		// prefixes below here are rarely, if ever, used in binary
		'h|hecto'       : [ 1e2, 1e2 ],
		'da|deka'       : [ 1e1, 1e1 ],
		'd|deci'        : [ 1e-1, 1e-1 ],
		'c|centi'       : [ 1e-2, 1e-2 ],
		'm|milli'       : [ 1e-3, 1e-3 ],
		'µ|micro'       : [ 1e-6, 1e-6 ],
		'n|nano'        : [ 1e-9, 1e-9 ],
		'p|pico'        : [ 1e-12, 1e-12 ],
		'f|femto'       : [ 1e-15, 1e-15 ],
		'a|atto'        : [ 1e-18, 1e-18 ],
		'z|zepto'       : [ 1e-21, 1e-21 ],
		'y|yocto'       : [ 1e-24, 1e-24 ]
	},
	// the \\d+ will not catch digits with spaces, commas or decimals; so use the value from n instead
	RegLong = '(\\d+)(\\s+)?([Zz]etta|[Ee]xa|[Pp]eta|[Tt]era|[Gg]iga|[Mm]ega|kilo|hecto|deka|deci|centi|milli|micro|nano|pico|femto|atto|zepto|yocto)(',
	RegAbbr = '(\\d+)(\\s+)?(Z|E|P|T|G|M|k|h|da|d|c|m|µ|n|p|f|a|z|y)(',
	// make these case-insensitive because we all forget the case for these binary values
	byteTest = /^[b|bit|byte|o|octet]/i;

	$.tablesorter.addParser({
		id: 'metric',
		is: function() {
			return false;
		},
		format: function(txt, table, cell, cellIndex) {
			var unit, isBinary, nameLong, nameAbbr,
				// default base unit name
				base = 'm|meter',
				// process number here to get a numerical format (us or eu)
				num = $.tablesorter.formatFloat( txt.replace(/[^\w,. \-()]/g, ''), table ),
				$t = table.config.$headerIndexed[ cellIndex ],
				regex = $t.data( 'metric' );
			if ( !regex ) {
				// stored values
				unit = ( $t.attr('data-metric-name') || base ).split( '|' );
				nameLong = $t.attr( 'data-metric-name-full' ) || '';
				nameAbbr = $t.attr( 'data-metric-name-abbr' ) || '';
				regex = [ nameLong || unit[1] || unit[0].substring(1), nameAbbr || unit[0] ];
				isBinary = byteTest.test( regex.join( '' ) );
				// adding 'data-metric-name-full' which would contain 'byte|BYTE|Byte' etc
				regex[2] = new RegExp( RegLong + (
					( nameLong === '' ? '' : nameLong + '|' + nameAbbr ) ||
					// with data-metric-name='b|byte', we end up with 'b|B|byte|BYTE' - maybe not the best solution for case-insensitivity
					( ( isBinary ? regex[0].toLowerCase() + '|' + regex[0].toUpperCase() : regex[0] ) + '|' +
					( isBinary ? regex[1].toLowerCase() + '|' + regex[1].toUpperCase() : regex[1] ) ) ) +
					')' );
				// adding 'data-metric-name-abbr' which would contain 'b|B' etc
				regex[3] = new RegExp( RegAbbr + ( nameAbbr ||
					( ( isBinary ? regex[1].toLowerCase() + '|' + regex[1].toUpperCase() : regex[1] ) ) ) +
					')' );
				$t.data( 'metric', regex );
			}
			// find match to full name or abbreviation
			unit = txt.match( regex[2] ) || txt.match( regex[3] );
			if ( unit ) {
				for ( base in prefixes ) {
					if ( unit[3].match( base ) ) {
						// exception when using binary prefix
						// change base for binary use
						isBinary = byteTest.test( unit[4] ) ? 1 : 0;
						return num * prefixes[ base ][ isBinary ];
					}
				}
			}
			return num;
		},
		type: 'numeric'
	});

})(jQuery);
