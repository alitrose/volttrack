// VoltTrack Chart.js Configuration Utilities (Luxury Noir & Bioluminescent Crimson Theme)

const ChartTheme = {
    crimson: "#FF2D55",
    crimsonLight: "rgba(255, 45, 85, 0.18)",
    coral: "#FF5E3A",
    coralLight: "rgba(255, 94, 58, 0.2)",
    amber: "#FF9500",
    rose: "#FF3B30",
    darkBurgundy: "#380C14",
    gridColor: "rgba(255, 255, 255, 0.06)",
    textColor: "#94A3B8"
};

function createUsageLineChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, "rgba(255, 45, 85, 0.35)");
    gradient.addColorStop(1, "rgba(255, 45, 85, 0.0)");

    return new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Daily Energy Consumption (kWh)",
                data: data,
                borderColor: ChartTheme.crimson,
                backgroundColor: gradient,
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: ChartTheme.crimson,
                pointBorderColor: "#fff",
                pointRadius: 3,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#050507",
                    titleColor: "#F8FAFC",
                    bodyColor: "#FF2D55",
                    borderColor: "rgba(255, 45, 85, 0.4)",
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                x: {
                    grid: { color: ChartTheme.gridColor },
                    ticks: { color: ChartTheme.textColor, font: { size: 11 } }
                },
                y: {
                    grid: { color: ChartTheme.gridColor },
                    ticks: { color: ChartTheme.textColor, font: { size: 11 } },
                    title: { display: true, text: "kWh", color: ChartTheme.textColor }
                }
            }
        }
    });
}

function createBillsBarChart(canvasId, labels, amounts) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Billed Amount (₹)",
                data: amounts,
                backgroundColor: ChartTheme.coral,
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#050507",
                    titleColor: "#fff",
                    bodyColor: "#FF5E3A",
                    borderColor: "rgba(255, 94, 58, 0.4)",
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => `Amount: ₹${ctx.raw.toLocaleString()}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: ChartTheme.textColor, font: { size: 11 } }
                },
                y: {
                    grid: { color: ChartTheme.gridColor },
                    ticks: { color: ChartTheme.textColor, font: { size: 11 } }
                }
            }
        }
    });
}

function createPeakDonutChart(canvasId, peakKwh, offpeakKwh) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Peak (18:00 - 22:00)", "Off-Peak"],
            datasets: [{
                data: [peakKwh, offpeakKwh],
                backgroundColor: [ChartTheme.crimson, ChartTheme.darkBurgundy],
                borderColor: "#050507",
                borderWidth: 3,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: ChartTheme.textColor, padding: 16, font: { size: 12 } }
                }
            },
            cutout: "70%"
        }
    });
}
