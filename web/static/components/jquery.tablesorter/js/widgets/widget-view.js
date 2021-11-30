/* Widget: view (beta) - updated 7/11/2016 (v2.26.6) */
/* By Justin F. Hallett (https://github.com/TheSin-)
 * Requires tablesorter v2.8+ and jQuery 1.7+
 */
/*jshint browser:true, jquery:true, unused:false */
/*global jQuery: false */
;(function($) {
	'use strict';

	var ts = $.tablesorter,
		is_hidden = false,
		tpos, ttop, tleft,

		view = ts.view = {
			copyCaption: function(c, wo) {
				view.removeCaption(c, wo);

				if (c.$table.find('caption').length > 0) {
					$(wo.view_caption).text(c.$table.find('caption').text());
				}
			},

			removeCaption: function(c, wo) {
				$(wo.view_caption).empty();
			},

			buildToolBar: function(c, wo) {
				view.removeToolBar(c, wo);
				view.copyCaption(c, wo);
				var $toolbar = $(wo.view_toolbar);

				$.each(wo.view_layouts, function(k, v) {
					var classes = wo.view_switcher_class;
					if (k === wo.view_layout) {
						classes += ' active';
					}

					var $switcher = $('<a>', {
						'href': '#',
						'class': classes,
						'data-view-type': k,
						'title': v.title
					});

					$switcher.append($('<i>', {
						'class': v.icon
					}));

					$toolbar.append($switcher);
				});

				$toolbar.find('.' + wo.view_switcher_class).on('click', function(e) {
					e.preventDefault();
					if ($(this).hasClass('active')) {
						// if currently clicked button has the active class
						// then we do nothing!
						return false;
					} else {
						// otherwise we are clicking on the inactive button
						// and in the process of switching views!
						$toolbar.find('.' + wo.view_switcher_class).removeClass('active');
						$(this).addClass('active');
						wo.view_layout = $(this).attr('data-view-type');

						if (wo.view_layouts[wo.view_layout].raw === true) {
							view.remove(c, wo);
							view.buildToolBar(c, wo);
						} else {
							if (is_hidden === false) {
								view.hideTable(c, wo);
							}
							view.buildView(c, wo);
						}
					}
				});
			},

			removeToolBar: function(c, wo) {
				$(wo.view_toolbar).empty();
				view.removeCaption(c, wo);
			},

			buildView: function(c, wo) {
				view.removeView(c, wo);

				var myview = wo.view_layouts[wo.view_layout];
				var $container = $(myview.container, {
					'class': wo.view_layout
				});

				ts.getColumnText(c.$table, 0, function(data) {
					var tmpl = myview.tmpl;

					$.each($(data.$row).find('td'), function(k, v) {
						var attrs = {};
						var reg = '{col' + k + '}';
						$.each(v.attributes, function(idx, attr) {
							attrs[attr.nodeName] = attr.nodeValue;
						});
						var content = $(v).html();
						// Add 2 spans, one is dropped when using .html()
						var span = $('<span />').append($('<span/>', attrs).append(content));
						tmpl = tmpl.replace(new RegExp(reg, 'g'), span.html());

						reg = '{col' + k + ':raw}';
						tmpl = tmpl.replace(new RegExp(reg, 'g'), $(v).text());
					});

					var $tmpl = $(tmpl);
					$.each(data.$row[0].attributes, function(idx, attr) {
						if (attr.nodeName === 'class') {
							$tmpl.attr(attr.nodeName, $tmpl.attr(attr.nodeName) + ' ' + attr.nodeValue);
						} else {
							$tmpl.attr(attr.nodeName, attr.nodeValue);
						}
					});
					$container.append($tmpl);
				});

				$(wo.view_container).append($container);
				c.$table.triggerHandler('viewComplete');
			},

			removeView: function(c, wo) {
				$(wo.view_container).empty();
			},

			hideTable: function(c) {
				tpos = c.$table.css('position');
				ttop = c.$table.css('bottom');
				tleft = c.$table.css('left');

				c.$table.css({
					'position': 'absolute',
					'top': '-10000px',
					'left': '-10000px'
				});

				is_hidden = true;
			},

			init: function(c, wo) {
				if (wo.view_layout === false) {
					return;
				}

				if (typeof wo.view_layouts[wo.view_layout] === 'undefined') {
					return;
				}

				if (is_hidden === false) {
					view.hideTable(c, wo);
				}

				c.$table.on('tablesorter-ready', function() {
					view.buildToolBar(c, wo);
					view.buildView(c, wo);
				});
			},

			remove: function(c, wo) {
				view.removeToolBar(c, wo);
				view.removeView(c, wo);

				c.$table.css({
					'position': tpos,
					'top': ttop,
					'left': tleft
				});

				is_hidden = false;
			}
		};

	ts.addWidget({
		id: 'view',
		options: {
			view_toolbar: '#ts-view-toolbar',
			view_container: '#ts-view',
			view_caption: '#ts-view-caption',
			view_switcher_class: 'ts-view-switcher',
			view_layout: false,
			view_layouts: {}
		},

		init: function(table, thisWidget, c, wo) {
			view.init(c, wo);
		},

		remove: function(table, c, wo) {
			view.remove(c, wo);
		}
	});

})(jQuery);
