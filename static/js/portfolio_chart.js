(function() {
    const ctx = document.getElementById('portfolioChart');
    const loadingEl = document.getElementById('chart-loading');
    const emptyEl = document.getElementById('chart-empty');
    const rangeSelector = document.getElementById('chart-range-selector');
    let chart = null;

    async function loadChartData(range = '1M') {
        loadingEl.style.display = 'block';
        emptyEl.style.display = 'none';
        if (ctx) ctx.style.display = 'none';

        try {
            const response = await fetch(`/trading/api/portfolio-history/?range=${range}`);
            const data = await response.json();

            loadingEl.style.display = 'none';

            if (!data.labels || data.labels.length === 0) {
                console.warn('No portfolio history data available');
                emptyEl.style.display = 'block';
                return;
            }

            ctx.style.display = 'block';
            renderChart(data);
        } catch (error) {
            console.error('Failed to load portfolio history:', error);
            loadingEl.style.display = 'none';
            emptyEl.style.display = 'block';
        }
    }

    function renderChart(data) {
        console.log('Rendering chart with data:', data);
        if (chart) {
            chart.destroy();
        }

        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Portfolio Value',
                        data: data.datasets.total_assets,
                        borderColor: 'rgb(13, 110, 253)',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: data.labels.length > 30 ? 0 : 3,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-GB', {
                                        style: 'currency',
                                        currency: data.currency || 'GBP'
                                    }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return new Intl.NumberFormat('en-GB', {
                                    style: 'currency',
                                    currency: data.currency || 'GBP',
                                    currencyDisplay: 'code',
                                    notation: 'standard',
                                }).format(value);
                            }
                        }
                    }
                }
            }
        });
    }

    // Range selector click handler
    rangeSelector.addEventListener('click', function(e) {
        if (e.target.dataset.range) {
            // Update active state
            rangeSelector.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            // Load new data
            loadChartData(e.target.dataset.range);
        }
    });

    // Initial load
    loadChartData('1M');
})();