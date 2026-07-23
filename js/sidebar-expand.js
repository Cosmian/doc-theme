/* Make no-link section headers expand/collapse the subtree on click.
   mdBook renders SUMMARY.md entries with an empty href as <div> instead
   of <a>, so they have no default click behaviour. This proxies those
   clicks to the adjacent <a class="toggle"> button that mdBook's own
   book.js already handles for fold/unfold. */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.chapter li.chapter-item > div').forEach(function (div) {
            var toggle = div.parentElement.querySelector('a.toggle');
            if (!toggle) return;
            div.addEventListener('click', function () {
                toggle.click();
            });
        });
    });
}());
