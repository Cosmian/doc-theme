/**
 * Version picker — populates #version-switcher-mount in the menu bar.
 *
 * Reads <path_to_root>versions.json which maps each section name to a
 * sorted array of semver tag strings (oldest → newest).
 *
 * Also hides versioned SUMMARY.md entries from the left sidebar (those
 * entries are required for mdBook to build the pages, but must not be
 * visible in the navigation tree).
 *
 * Visible on:
 *   - Versioned pages  /<section>/<X.Y.Z>/…  (current version selected)
 *   - Latest pages     /<section>/…           ("latest" selected)
 */
(function () {
  'use strict';

  var VERSIONED_RE = /^\/([a-z_]+)\/(\d+\.\d+\.\d+)(\/.*)?/;

  /* ── Styles for the picker widget ─────────────────────────────────── */
  function injectPickerCSS() {
    if (document.getElementById('vp-css')) return;
    var style = document.createElement('style');
    style.id = 'vp-css';
    style.textContent = [
      '#version-switcher-mount { align-items: center; gap: 6px; padding: 0 8px; }',
      '.vp-label { font-size: .82rem; color: var(--icons); white-space: nowrap; }',
      '.vp-select { background: var(--bg); color: var(--fg);',
      '  border: 1px solid var(--icons); border-radius: 4px;',
      '  padding: 2px 6px; cursor: pointer; font-size: .82rem; max-width: 9em; }',
      '.vp-select:hover, .vp-select:focus { border-color: var(--links); outline: none; }',
    ].join('\n');
    document.head.appendChild(style);
  }

  /* ── Hide versioned chapter items and their "X Versions" parents ─── */
  function hideVersionedSidebar(data) {
    // Collect all versioned URL path prefixes from versions.json
    var prefixes = [];
    Object.keys(data).forEach(function (section) {
      data[section].forEach(function (v) {
        prefixes.push('/' + section + '/' + v + '/');
      });
    });

    function process() {
      // Hide individual versioned chapter links.
      // a.href is always absolute, so new URL(a.href).pathname is path-depth-independent.
      document.querySelectorAll('.chapter-item a[href]').forEach(function (a) {
        try {
          var pathname = new URL(a.href).pathname;
          for (var i = 0; i < prefixes.length; i++) {
            if (pathname.startsWith(prefixes[i])) {
              var li = a.closest('li');
              if (li) li.style.display = 'none';
              break;
            }
          }
        } catch (e) {}
      });

      // Hide "X Versions" parent group headers.
      // mdBook renders non-linked chapters as <div> (not <a>) inside .chapter-item.
      document.querySelectorAll('.chapter-item > div').forEach(function (div) {
        if (!/ Versions$/.test(div.textContent.trim())) return;
        var li = div.closest('li');
        if (!li) return;
        li.style.display = 'none';
        // The children are in the immediately following <li><ol class="section">
        var next = li.nextElementSibling;
        if (next) next.style.display = 'none';
      });
    }

    process();

    // Safety net: if sidebar is populated asynchronously, catch it via MutationObserver
    var scrollbox = document.querySelector('mdbook-sidebar-scrollbox');
    if (scrollbox && !scrollbox.firstElementChild) {
      var obs = new MutationObserver(function () { process(); obs.disconnect(); });
      obs.observe(scrollbox, { childList: true });
    }
  }

  /* ── Render the version picker in the menu bar ─────────────────────── */
  function render(current, versions, urlFor) {
    var mount = document.getElementById('version-switcher-mount');
    if (!mount) return;
    injectPickerCSS();

    var opts = [
      '<option value="latest"' + (current === 'latest' ? ' selected' : '') + '>latest</option>',
    ];
    versions.slice().reverse().forEach(function (v) {
      opts.push(
        '<option value="' + v + '"' + (v === current ? ' selected' : '') + '>' + v + '</option>'
      );
    });

    mount.innerHTML =
      '<label class="vp-label" for="vp-select">Version</label>' +
      '<select id="vp-select" class="vp-select">' + opts.join('') + '</select>';

    document.getElementById('vp-select').addEventListener('change', function (e) {
      window.location.pathname = urlFor(e.target.value);
    });

    mount.style.display = 'inline-flex';
  }

  function init() {
    /* path_to_root is injected by mdBook into every page */
    /* global path_to_root */
    var root = typeof path_to_root !== 'undefined' ? path_to_root : '';
    var path = window.location.pathname;
    var vm   = path.match(VERSIONED_RE);

    fetch(root + 'versions.json')
      .then(function (r) { return r.json(); })
      .then(function (data) {

        /* Always hide versioned sidebar entries on every page */
        hideVersionedSidebar(data);

        /* ── version picker ── */
        if (vm && data[vm[1]]) {
          /* Versioned page: /<section>/<X.Y.Z>/rest */
          var sec = vm[1], cur = vm[2], rest = vm[3] || '/index.html';
          render(cur, data[sec], function (v) {
            return v === 'latest' ? '/' + sec + rest : '/' + sec + '/' + v + rest;
          });
          return;
        }

        /* Latest section page: /<section>/rest */
        Object.keys(data).forEach(function (s) {
          var sm = path.match(new RegExp('^\/' + s.replace('.', '\\.') + '(\/.+)?$'));
          if (!sm) return;
          var rest = sm[1] || '/index.html';
          render('latest', data[s], function (v) {
            return v === 'latest' ? '/' + s + rest : '/' + s + '/' + v + rest;
          });
        });

      })
      .catch(function () { /* versions.json not present — no picker, no hiding */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
