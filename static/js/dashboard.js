document.addEventListener("DOMContentLoaded", function () {
    const progressBars = document.querySelectorAll("[data-progress]");

    progressBars.forEach(function (bar) {
        let percentage = Number(bar.dataset.progress);

        if (!Number.isFinite(percentage)) {
            percentage = 0;
        }

        percentage = Math.max(0, Math.min(100, percentage));

        bar.style.width = percentage + "%";
    });
});
