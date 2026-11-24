const actions = JSON.parse(document.querySelector("#action-data").textContent);
const statuses = JSON.parse(document.querySelector("#status-data").textContent);

Chart.defaults.color = "#edf2f5";
Chart.defaults.borderColor = "#455765";

new Chart(document.querySelector("#action-chart"), {
    type: "bar",
    data: {
        labels: actions.map(row => row.label),
        datasets: [{
            label: "예측 건수",
            data: actions.map(row => row.count),
            backgroundColor: "#76c7bc",
        }],
    },
    options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { beginAtZero: true, ticks: { precision: 0 } },
        },
    },
});

new Chart(document.querySelector("#status-chart"), {
    type: "doughnut",
    data: {
        labels: statuses.map(row => row.label),
        datasets: [{
            label: "작업 건수",
            data: statuses.map(row => row.count),
            backgroundColor: ["#e3bb71", "#78a9dc", "#76c7bc", "#e18e91"],
        }],
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
    },
});
