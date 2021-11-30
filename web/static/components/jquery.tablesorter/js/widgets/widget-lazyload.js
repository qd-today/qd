/*! Widget: lazyload (BETA) - 4/1/2016 (v2.25.7) *//*
 * Requires tablesorter v2.8+ and jQuery 1.7+
 * by Rob Garrison
 */
/*jshint browser:true, jquery:true, unused:false */
;( function( $, window ) {
	'use strict';
	var ts = $.tablesorter;

	ts.lazyload = {
		init : function( c, wo ) {
			if ( wo.lazyload_event === 'scrollstop' && !ts.addScrollStopDone ) {
				ts.addScrollStop();
				ts.addScrollStopDone = true;
				$.event.special.scrollstop.latency = wo.lazyload_latency || 250;
			}
			ts.lazyload.update( c, wo );
			var namespace = c.namespace + 'lazyload ',
				events = [
					wo.lazyload_update,
					'pagerUpdate',
					wo.columnSelector_updated || 'columnUpdate',
					''
				].join( namespace );
			c.$table
				.on( events, function() {
					ts.lazyload.update( c, c.widgetOptions );
				})
				.on( 'filterEnd' + namespace, function() {
					// give lazyload a nudge after filtering the table. Fixes #1169
					$(window).scroll();
				});
		},
		update : function( c, wo ) {
			// add '.' if not already included
			var sel = ( /(\.|#)/.test( wo.lazyload_imageClass ) ? '' : '.' ) + wo.lazyload_imageClass;
			c.$table.find( sel ).lazyload({
				threshold       : wo.lazyload_threshold,
				failure_limit   : wo.lazyload_failure_limit,
				event           : wo.lazyload_event,
				effect          : wo.lazyload_effect,
				container       : wo.lazyload_container,
				data_attribute  : wo.lazyload_data_attribute,
				skip_invisible  : wo.lazyload_skip_invisible,
				appear          : wo.lazyload_appear,
				load            : wo.lazyload_load,
				placeholder     : wo.lazyload_placeholder
			});
			// give lazyload a nudge after updating the table. Fixes #1169
			setTimeout(function() {
				$(window).scroll();
			}, 1);
		},
		remove : function( c ) {
			c.$table.off( c.namespace + 'lazyload' );
		}
	};

	ts.addWidget({
		id: 'lazyload',
		options: {
			// widget options
			lazyload_imageClass     : 'lazy',
			lazyload_update         : 'lazyloadUpdate',
			// scrollStop option (https://github.com/ssorallen/jquery-scrollstop)
			lazyload_latency        : 250,
			// lazyload options (see http://www.appelsiini.net/projects/lazyload)
			lazyload_threshold      : 0,
			lazyload_failure_limit  : 0,
			lazyload_event          : 'scrollstop',
			lazyload_effect         : 'show',
			lazyload_container      : window,
			lazyload_data_attribute : 'original',
			lazyload_skip_invisible : true,
			lazyload_appear         : null,
			lazyload_load           : null,
			lazyload_placeholder    : 'data:image/gif;base64,R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
		},
		init: function( table, thisWidget, c, wo ) {
			ts.lazyload.init( c, wo );
		},
		remove : function( table, c, wo ) {
			ts.lazyload.remove( c, wo );
		}
	});

	// jscs:disable
	ts.addScrollStop = function() {
		// jQuery Scrollstop Plugin v1.2.0
		// https://github.com/ssorallen/jquery-scrollstop
		/*
		(function (factory) {
		// UMD[2] wrapper for jQuery plugins to work in AMD or in CommonJS.
		//
		// [2] https://github.com/umdjs/umd

		if (typeof define === 'function' && define.amd) {
		// AMD. Register as an anonymous module.
		define(['jquery'], factory);
		} else if (typeof exports === 'object') {
		// Node/CommonJS
		module.exports = factory(require('jquery'));
		} else {
		// Browser globals
		factory(jQuery);
		}
		}(function ($) { */
		// $.event.dispatch was undocumented and was deprecated in jQuery 1.7[1]. It
		// was replaced by $.event.handle in jQuery 1.9.
		//
		// Use the first of the available functions to support jQuery <1.8.
		//
		// [1] https://github.com/jquery/jquery-migrate/blob/master/src/event.js#L25
		var dispatch = $.event.dispatch || $.event.handle;

		var special = $.event.special,
			uid1 = 'D' + (+new Date()),
			uid2 = 'D' + (+new Date() + 1);

		special.scrollstart = {
			setup: function(data) {
				var _data = $.extend({
					latency: special.scrollstop.latency
				}, data);

				var timer,
					handler = function(evt) {
						var _self = this,
							_args = arguments;
						if (timer) {
							clearTimeout(timer);
						} else {
							evt.type = 'scrollstart';
							dispatch.apply(_self, _args);
						}
						timer = setTimeout(function() {
							timer = null;
						}, _data.latency);
					};
				$(this).bind('scroll', handler).data(uid1, handler);
			},
			teardown: function() {
				$(this).unbind('scroll', $(this).data(uid1));
			}
		};
		special.scrollstop = {
			latency: 250,
			setup: function(data) {
				var _data = $.extend({
					latency: special.scrollstop.latency
				}, data);
				var timer,
					handler = function(evt) {
						var _self = this,
						_args = arguments;
						if (timer) {
							clearTimeout(timer);
						}
						timer = setTimeout(function() {
							timer = null;
							evt.type = 'scrollstop';
							dispatch.apply(_self, _args);
						}, _data.latency);
					};
				$(this).bind('scroll', handler).data(uid2, handler);
			},
			teardown: function() {
				$(this).unbind('scroll', $(this).data(uid2));
			}
		};
	/*
	}));
	*/

	};
	// jscs:enable

})( jQuery, window );

// jscs:disable
/*!
* Lazy Load - jQuery plugin for lazy loading images
*
* Copyright (c) 2007-2015 Mika Tuupola
*
* Licensed under the MIT license:
*   http://www.opensource.org/licenses/mit-license.php
*
* Project home:
*   http://www.appelsiini.net/projects/lazyload
*
* Version:  1.9.7
*
*/
(function($, window, document, undefined) {
	var $window = $(window);
	$.fn.lazyload = function(options) {
		var elements = this;
		var $container;
		var settings = {
			threshold       : 0,
			failure_limit   : 0,
			event           : 'scroll',
			effect          : 'show',
			container       : window,
			data_attribute  : 'original',
			skip_invisible  : false,
			appear          : null,
			load            : null,
			placeholder     : 'data:image/gif;base64,R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
		};
		function update() {
			var counter = 0;
			elements.each(function() {
				var $this = $(this);
				if (settings.skip_invisible && !$this.is(':visible')) {
					return;
				}
				if ($.abovethetop(this, settings) || $.leftofbegin(this, settings)) {
					/* Nothing. */
				} else if (!$.belowthefold(this, settings) && !$.rightoffold(this, settings)) {
					$this.trigger('appear');
					/* if we found an image we'll load, reset the counter */
					counter = 0;
				} else {
					if (++counter > settings.failure_limit) {
						return false;
					}
				}
			});
		}
		if (options) {
			/* Maintain BC for a couple of versions. */
			if (undefined !== options.failurelimit) {
				options.failure_limit = options.failurelimit;
				delete options.failurelimit;
			}
			if (undefined !== options.effectspeed) {
				options.effect_speed = options.effectspeed;
				delete options.effectspeed;
			}
			$.extend(settings, options);
		}
		/* Cache container as jQuery as object. */
		$container = (settings.container === undefined ||
		settings.container === window) ? $window : $(settings.container);
		/* Fire one scroll event per scroll. Not one scroll event per image. */
		if (0 === settings.event.indexOf('scroll')) {
			$container.bind(settings.event, function() {
				return update();
			});
		}
		this.each(function() {
			var self = this;
			var $self = $(self);
			self.loaded = false;
			/* If no src attribute given use data:uri. */
			if ($self.attr('src') === undefined || $self.attr('src') === false) {
				if ($self.is('img')) {
					$self.attr('src', settings.placeholder);
				}
			}
			/* When appear is triggered load original image. */
			$self.one('appear', function() {
				if (!this.loaded) {
					if (settings.appear) {
						var elements_left = elements.length;
						settings.appear.call(self, elements_left, settings);
					}
					$('<img />')
						.bind('load', function() {
							var original = $self.attr('data-' + settings.data_attribute);
							$self.hide();
							if ($self.is('img')) {
								$self.attr('src', original);
							} else {
								$self.css('background-image', 'url("' + original + '")');
							}
							$self[settings.effect](settings.effect_speed);
							self.loaded = true;
							/* Remove image from array so it is not looped next time. */
							var temp = $.grep(elements, function(element) {
								return !element.loaded;
							});
							elements = $(temp);
							if (settings.load) {
								var elements_left = elements.length;
								settings.load.call(self, elements_left, settings);
							}
						})
						.attr('src', $self.attr('data-' + settings.data_attribute));
				}
			});
			/* When wanted event is triggered load original image */
			/* by triggering appear.                              */
			if (0 !== settings.event.indexOf('scroll')) {
				$self.bind(settings.event, function() {
					if (!self.loaded) {
						$self.trigger('appear');
					}
				});
			}
		});
		/* Check if something appears when window is resized. */
		$window.bind('resize', function() {
			update();
		});
		/* With IOS5 force loading images when navigating with back button. */
		/* Non optimal workaround. */
		if ((/(?:iphone|ipod|ipad).*os 5/gi).test(navigator.appVersion)) {
			$window.bind('pageshow', function(event) {
				if (event.originalEvent && event.originalEvent.persisted) {
					elements.each(function() {
						$(this).trigger('appear');
					});
				}
			});
		}
		/* Force initial check if images should appear. */
		$(document).ready(function() {
			update();
		});
		return this;
	};
	/* Convenience methods in jQuery namespace.           */
	/* Use as  $.belowthefold(element, {threshold : 100, container : window}) */
	$.belowthefold = function(element, settings) {
		var fold;
		if (settings.container === undefined || settings.container === window) {
			fold = (window.innerHeight ? window.innerHeight : $window.height()) + $window.scrollTop();
		} else {
			fold = $(settings.container).offset().top + $(settings.container).height();
		}
		return fold <= $(element).offset().top - settings.threshold;
	};
	$.rightoffold = function(element, settings) {
		var fold;
		if (settings.container === undefined || settings.container === window) {
			fold = $window.width() + $window.scrollLeft();
		} else {
			fold = $(settings.container).offset().left + $(settings.container).width();
		}
		return fold <= $(element).offset().left - settings.threshold;
	};
	$.abovethetop = function(element, settings) {
		var fold;
		if (settings.container === undefined || settings.container === window) {
			fold = $window.scrollTop();
		} else {
			fold = $(settings.container).offset().top;
		}
		return fold >= $(element).offset().top + settings.threshold  + $(element).height();
	};
	$.leftofbegin = function(element, settings) {
		var fold;
		if (settings.container === undefined || settings.container === window) {
			fold = $window.scrollLeft();
		} else {
			fold = $(settings.container).offset().left;
		}
		return fold >= $(element).offset().left + settings.threshold + $(element).width();
	};
	$.inviewport = function(element, settings) {
		return !$.rightoffold(element, settings) && !$.leftofbegin(element, settings) &&
		!$.belowthefold(element, settings) && !$.abovethetop(element, settings);
	};
	/* Custom selectors for your convenience.   */
	/* Use as $('img:below-the-fold').something() or */
	/* $('img').filter(':below-the-fold').something() which is faster */
	$.extend($.expr[':'], {
		'below-the-fold' : function(a) { return $.belowthefold(a, {threshold : 0}); },
		'above-the-top'  : function(a) { return !$.belowthefold(a, {threshold : 0}); },
		'right-of-screen': function(a) { return $.rightoffold(a, {threshold : 0}); },
		'left-of-screen' : function(a) { return !$.rightoffold(a, {threshold : 0}); },
		'in-viewport'    : function(a) { return $.inviewport(a, {threshold : 0}); },
		/* Maintain BC for couple of versions. */
		'above-the-fold' : function(a) { return !$.belowthefold(a, {threshold : 0}); },
		'right-of-fold'  : function(a) { return $.rightoffold(a, {threshold : 0}); },
		'left-of-fold'   : function(a) { return !$.rightoffold(a, {threshold : 0}); }
	});
})(jQuery, window, document);
