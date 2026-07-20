/**
 * old-versions-link.js
 *
 * Injects a single "All versions" link into the right-hand side of the
 * top banner (#version-switcher-mount) on every page.
 *
 * The link points to the combined versions index at /versions/ which
 * lists every available version of every product (KMS, Findex, Cosmian VM).
 * That page is built independently of mdBook by build-versions-index.py.
 */
(function () {
  'use strict';

  function init() {
    var mount = document.getElementById('version-switcher-mount');
    if (!mount) return;

    var style = document.createElement('style');
    style.textContent = [
      '#version-switcher-mount { align-items: center; padding: 0 8px; }',
      '.ov-link { font-size: .82rem; color: var(--icons); white-space: nowrap;',
      '  text-decoration: none; border: 1px solid currentColor;',
      '  border-radius: 4px; padding: 2px 8px; }',
      '.ov-link:hover { color: var(--links); }',
    ].join('\n');
    document.head.appendChild(style);

    mount.innerHTML = '<a class="ov-link" href="/versions/">All versions</a>';
    mount.style.display = 'inline-flex';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
