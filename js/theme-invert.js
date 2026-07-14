/* Light / dark toggle for the Eviden documentation site.
   Switches between the book's default-theme (light) and preferred-dark-theme
   (navy) and keeps the moon/sun icon in sync. */
(function () {
    'use strict';

    var DARK_THEMES  = ['coal', 'navy', 'ayu'];
    var DARK_TARGET  = 'navy';   // preferred dark theme
    var LIGHT_TARGET = 'light';  // preferred light theme
    var ALL_THEMES   = ['coal', 'navy', 'ayu', 'rust', 'light'];

    function currentTheme() {
        return localStorage.getItem('mdbook-theme') || LIGHT_TARGET;
    }

    function isDark(theme) {
        return DARK_THEMES.indexOf(theme) !== -1;
    }

    function applyTheme(theme) {
        var html = document.documentElement;
        ALL_THEMES.forEach(function (t) { html.classList.remove(t); });
        html.classList.add(theme);
        localStorage.setItem('mdbook-theme', theme);
    }

    function syncIcon(btn) {
        var dark = isDark(currentTheme());
        var icon = btn.querySelector('i');
        icon.className = dark ? 'fa fa-sun-o' : 'fa fa-moon-o';
        var label = dark ? 'Switch to light theme' : 'Switch to dark theme';
        btn.setAttribute('title', label);
        btn.setAttribute('aria-label', label);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('theme-invert');
        if (!btn) return;

        syncIcon(btn);

        btn.addEventListener('click', function () {
            var next = isDark(currentTheme()) ? LIGHT_TARGET : DARK_TARGET;
            applyTheme(next);
            syncIcon(btn);
            // Mermaid diagrams are rendered once at page load; a reload is the
            // only way to re-render them in the new theme (same strategy as
            // mermaid-init.js uses for the theme-selector popup buttons).
            window.location.reload();
        });
    });
}());
