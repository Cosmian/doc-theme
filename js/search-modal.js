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

/* Highlights query terms in result titles. searcher.js only wraps matches
   in <em> inside the body teaser, never in the title/breadcrumb line; doing
   it here (instead of forking that vendored file) keeps this our code, not
   a copy of mdBook's that would stop tracking future mdBook upgrades. */
(function () {
    'use strict';

    function escapeRegExp(s) {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightTitles(searchterms) {
        var pattern = new RegExp('(' + searchterms.map(escapeRegExp).join('|') + ')', 'gi');
        document.querySelectorAll('#searchresults > li > a').forEach(function (a) {
            // Title text is plain (no nested tags), so replacing on innerHTML is safe.
            a.innerHTML = a.innerHTML.replace(pattern, '<mark>$1</mark>');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var results = document.getElementById('searchresults');
        var searchbar = document.getElementById('searchbar');
        if (!results || !searchbar) return;

        // childList (no subtree): fires once per searcher.js result batch,
        // not for our own <mark> edits nested inside those <li>/<a> nodes.
        var observer = new MutationObserver(function (mutations) {
            var hasNewResults = mutations.some(function (m) { return m.addedNodes.length > 0; });
            if (!hasNewResults) return;
            var searchterms = searchbar.value.trim().split(/\s+/).filter(Boolean);
            if (searchterms.length) highlightTitles(searchterms);
        });
        observer.observe(results, { childList: true });
    });
}());
