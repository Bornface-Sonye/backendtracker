document.getElementById("toggleSidebar").onclick = function() {
    document.getElementById("sidebar").classList.toggle("collapsed");
};

document.querySelectorAll(".load-link").forEach(link => {
    link.onclick = function(event) {
        event.preventDefault();
        let url = this.getAttribute("data-url");
        fetch(url)
            .then(response => response.text())
            .then(html => {
                document.getElementById("hero-section").innerHTML = html;
                window.history.pushState({}, "", url);
            });
    };
});
