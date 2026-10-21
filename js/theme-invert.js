/* Light / dark toggle for the Eviden documentation site.
   Switches between the book's default-theme (light) and preferred-dark-theme
   (navy) and keeps the moon/sun icon in sync. */
(function () {
    'use strict';

    var DARK_THEME   = 'navy';
    var LIGHT_THEME  = 'light';

    function currentTheme() {
        return localStorage.getItem('mdbook-theme') || LIGHT_THEME;
    }

    function isDark(theme) {
        return theme === DARK_THEME;
    }

    function applyTheme(theme) {
        var html = document.documentElement;
        html.classList.remove(DARK_THEME, LIGHT_THEME);
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
            var next = isDark(currentTheme()) ? LIGHT_THEME : DARK_THEME;
            applyTheme(next);
            syncIcon(btn);
            // Mermaid diagrams are rendered once at page load; a reload is the
            // only way to re-render them in the new theme (same strategy as
            // mermaid-init.js uses for the theme-selector popup buttons).
            window.location.reload();
        });
    });
}());
