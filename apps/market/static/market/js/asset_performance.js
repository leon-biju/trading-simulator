document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('assetChart');
    if (canvas) {
        const timestamps = JSON.parse(canvas.dataset.timestamps);
        const prices = JSON.parse(canvas.dataset.prices);
        const currencyCode = canvas.dataset.currencyCode;

        const ctx = canvas.getContext('2d');
        const assetChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: `Price (${currencyCode})`,
                    data: prices,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Timestamp'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Price'
                        },
                        beginAtZero: false
                    }
                }
            }
        });
    }
});
