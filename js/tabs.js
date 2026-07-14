// Self-contained tabbed content behaviour (replaces the mdbook-tabs plugin).
(function () {
    function activate(container, index) {
        var links = [];
        var panels = [];
        for (var i = 0; i < container.children.length; i++) {
            var child = container.children[i];
            if (child.classList.contains("tab-headers")) {
                for (var j = 0; j < child.children.length; j++) {
                    if (child.children[j].classList.contains("tab-link")) {
                        links.push(child.children[j]);
                    }
                }
            } else if (child.classList.contains("tab-content")) {
                panels.push(child);
            }
        }
        links.forEach(function (l, i) {
            l.classList.toggle("active", i === index);
        });
        panels.forEach(function (p, i) {
            p.classList.toggle("active", i === index);
        });
    }

    function init() {
        var containers = document.querySelectorAll(".tabs");
        containers.forEach(function (container) {
            var headers = container.querySelector(":scope > .tab-headers");
            if (!headers) return;
            var links = headers.querySelectorAll(":scope > .tab-link");
            links.forEach(function (link, index) {
                link.addEventListener("click", function () {
                    activate(container, index);
                });
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
