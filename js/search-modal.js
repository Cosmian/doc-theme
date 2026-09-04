/* Closes the search popup (see eviden.css) when clicking its backdrop.
   Reuses the existing #search-toggle click handler so state (aria-expanded,
   focus, etc.) stays in sync with searcher.js. */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        var wrap = document.getElementById('search-wrapper');
        var toggle = document.getElementById('search-toggle');
        if (!wrap || !toggle) return;
        wrap.addEventListener('mousedown', function (e) {
            if (e.target === wrap) toggle.click();
        });
    });
}());
