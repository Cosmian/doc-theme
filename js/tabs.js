// Tabbed content behaviour — compatible with the mdbook-tabs preprocessor.
const changeTab = (container, name) => {
    for (const child of container.children) {
        if (!(child instanceof HTMLElement)) continue;
        if (child.classList.contains('mdbook-tabs')) {
            for (const tab of child.children) {
                if (!(tab instanceof HTMLElement)) continue;
                tab.classList.toggle('active', tab.dataset.tabname === name);
            }
        } else if (child.classList.contains('mdbook-tab-content')) {
            child.classList.toggle('hidden', child.dataset.tabname !== name);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    for (const tab of document.querySelectorAll('.mdbook-tab')) {
        tab.addEventListener('click', () => {
            if (!(tab instanceof HTMLElement)) return;
            const nav = tab.parentElement;
            if (!nav || !nav.parentElement) return;
            const container = nav.parentElement;
            const name = tab.dataset.tabname;
            const global = container.dataset.tabglobal;
            changeTab(container, name);
            if (global) {
                localStorage.setItem(`mdbook-tabs-${global}`, name);
                for (const gc of document.querySelectorAll(
                    `.mdbook-tabs-container[data-tabglobal="${global}"]`
                )) {
                    changeTab(gc, name);
                }
            }
        });
    }
    for (const container of document.querySelectorAll(
        '.mdbook-tabs-container[data-tabglobal]'
    )) {
        const global = container.dataset.tabglobal;
        const name = localStorage.getItem(`mdbook-tabs-${global}`);
        if (name && document.querySelector(`.mdbook-tab[data-tabname="${name}"]`)) {
            changeTab(container, name);
        }
    }
});
