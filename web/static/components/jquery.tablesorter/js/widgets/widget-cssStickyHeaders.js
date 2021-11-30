/*! Widget: cssStickyHeaders - updated 6/16/2018 (v2.30.6) *//*
* Requires a modern browser, tablesorter v2.8+
*/
/*jshint jquery:true, unused:false */
;(function($, window) {
	'use strict';

	var ts = $.tablesorter;

	function cssStickyHeadersInit(c, wo) {
		var offst, adjustY,
			$table = c.$table,
			$attach = $(wo.cssStickyHeaders_attachTo),
			// target all versions of IE
			isIE = 'ActiveXObject' in window || window.navigator.userAgent.indexOf('Edge') > -1,
			namespace = c.namespace + 'cssstickyheader ',
			$thead = $table.children('thead'),
			$caption = $table.children('caption'),
			$win = $attach.length ? $attach : $(window),
			$parent = $table.parent().closest('table.' + ts.css.table),
			$parentThead = $parent.length && ts.hasWidget($parent[0], 'cssStickyHeaders') ? $parent.children('thead') : [],
			borderTopWidth = ( parseInt( $table.css('border-top-width'), 10 ) || 0 ),
			// Fixes for Safari
			tableH = $table.height(),
			lastCaptionSetting = wo.cssStickyHeaders_addCaption,
			// table offset top changes while scrolling in FF
			adjustOffsetTop = false,
			addCaptionHeight = false,
			setTransform = function( $elms, y ) {
				var translate = y === 0 ? '' : 'translate(0px,' + y + 'px)';
				$elms.css({
					'transform' : translate,
					'-ms-transform' : translate,
					'-webkit-transform' : translate
				});
			};

		// Firefox fixes
		if ($caption.length) {
			// Firefox does not include the caption height when getting the table height
			// see https://bugzilla.mozilla.org/show_bug.cgi?id=820891, so lets detect it instead of browser sniff
			$caption.hide();
			addCaptionHeight = $table.height() === tableH;
			$caption.show();

			// Firefox changes the offset().top when translating the table caption
			offst = $table.offset().top;
			setTransform( $caption, 20 );
			adjustOffsetTop = $table.offset().top !== offst;
			setTransform( $caption, 0 );
		}

		$win
		.unbind( ('scroll resize '.split(' ').join(namespace)).replace(/\s+/g, ' ') )
		.bind('scroll resize '.split(' ').join(namespace), function() {
			// make sure "wo" is current otherwise changes to widgetOptions
			// are not dynamic (like the add caption button in the demo)
			wo = c.widgetOptions;

			if ( adjustOffsetTop ) {
				// remove transform from caption to get the correct offset().top value
				setTransform( $caption, 0 );
				adjustY = $table.offset().top;
			}

			// Fix for safari, when caption present, table
			// height changes while scrolling
			if ($win.scrollTop() < $caption.outerHeight(true)) {
				tableH = $table.height();
			}

			var top = $attach.length ? $attach.offset().top : $win.scrollTop(),
			// add caption height; include table padding top & border-spacing or text may be above the fold (jQuery UI themes)
			// border-spacing needed in Firefox, but not webkit... not sure if I should account for that
			captionHeight = ( $caption.outerHeight(true) || 0 ) +
				( parseInt( $table.css('padding-top'), 10 ) || 0 ) +
				( parseInt( $table.css('border-spacing'), 10 ) || 0 ),

			bottom = tableH + ( addCaptionHeight && wo.cssStickyHeaders_addCaption ? captionHeight : 0 ) -
				$thead.height() - ( $table.children('tfoot').height() || 0 ) -
				( wo.cssStickyHeaders_addCaption ? captionHeight : ( addCaptionHeight ? 0 : captionHeight ) ),

			parentTheadHeight = $parentThead.length ? $parentThead.height() : 0,

			// get bottom of nested sticky headers
			nestedStickyBottom = $parentThead.length ? (
					isIE ? $parent.data('cssStickyHeaderBottom') + parentTheadHeight :
					$parentThead.offset().top + parentTheadHeight - $win.scrollTop()
				) : 0,

			// in this case FF's offsetTop changes while scrolling, so we get a saved offsetTop before scrolling occurs
			// but when the table is inside a wrapper ($attach) we need to continually update the offset top
			tableOffsetTop = adjustOffsetTop ? adjustY : $table.offset().top,

			offsetTop = addCaptionHeight ? tableOffsetTop - ( wo.cssStickyHeaders_addCaption ? captionHeight : 0 ) : tableOffsetTop,

			// Detect nested tables - fixes #724
			deltaY = top - offsetTop + nestedStickyBottom + borderTopWidth + ( wo.cssStickyHeaders_offset || 0 ) -
				( wo.cssStickyHeaders_addCaption ? ( addCaptionHeight ? captionHeight : 0 ) : captionHeight ),

			finalY = deltaY > 0 && deltaY <= bottom ? deltaY : 0,

			// All IE (even IE11) can only transform header cells - fixes #447 thanks to @gakreol!
			$cells = isIE ? $thead.children().children() : $thead;

			// more crazy IE stuff...
			if (isIE) {
				// I didn't bother testing 3 nested tables deep in IE, because I hate it
				c.$table.data( 'cssStickyHeaderBottom', ( $parentThead.length ? parentTheadHeight : 0 ) -
					( wo.cssStickyHeaders_addCaption ? captionHeight : 0 ) );
			}

			if (wo.cssStickyHeaders_addCaption) {
				$cells = $cells.add($caption);
			}
			if (lastCaptionSetting !== wo.cssStickyHeaders_addCaption) {
				lastCaptionSetting = wo.cssStickyHeaders_addCaption;
				// reset caption position if addCaption option is dynamically changed to false
				if (!lastCaptionSetting) {
					setTransform( $caption, 0 );
				}
			}

			setTransform( $cells, finalY );

		});
		$table
			.unbind( ('filterEnd updateComplete '.split(' ').join(namespace)).replace(/\s+/g, ' ') )
			.bind('filterEnd' + namespace, function() {
				if (wo.cssStickyHeaders_filteredToTop) {
					// scroll top of table into view
					window.scrollTo(0, $table.position().top);
				}
			})
			.bind('updateComplete' + namespace, function() {
				cssStickyHeadersInit(c, c.widgetOptions);
			});
	}

	ts.addWidget({
		id: 'cssStickyHeaders',
		priority: 10,
		options: {
			cssStickyHeaders_offset        : 0,
			cssStickyHeaders_addCaption    : false,
			// jQuery selector or object to attach sticky header to
			cssStickyHeaders_attachTo      : null,
			cssStickyHeaders_filteredToTop : true
		},
		init : function(table, thisWidget, c, wo) {
			cssStickyHeadersInit(c, wo);
		},
		remove: function(table, c, wo, refreshing) {
			if (refreshing) { return; }
			var namespace = c.namespace + 'cssstickyheader ';
			$(window).unbind( ('scroll resize '.split(' ').join(namespace)).replace(/\s+/g, ' ') );
			c.$table
				.unbind( ('filterEnd scroll resize updateComplete '.split(' ').join(namespace)).replace(/\s+/g, ' ') )
				.add( c.$table.children('thead').children().children() )
				.children('thead, caption').css({
					'transform' : '',
					'-ms-transform' : '',
					'-webkit-transform' : ''
				});
		}
	});

})(jQuery, window);
