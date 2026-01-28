document.addEventListener('DOMContentLoaded', () => {
    const chartLoader = document.getElementById('chart-loader');
    if (!chartLoader) {
        return;
    }

    const baseUrl = chartLoader.dataset.chartUrl;
    const defaultRange = chartLoader.dataset.defaultRange || 'month';
    const rangeButtons = document.querySelectorAll('[data-range]');
    let chart = null;

    const setActiveRange = (range) => {
        rangeButtons.forEach((button) => {
            button.classList.toggle('active', button.dataset.range === range);
        });
    };

    const parseDateValue = (value) => {
        if (value.includes('T')) {
            return new Date(value);
        }
        return new Date(`${value}T00:00:00`);
    };

    const buildCandleSeries = (data) => data.candlestick_data.map((item) => ({
        x: parseDateValue(item.x),
        y: [item.o, item.h, item.l, item.c]
    }));

    const buildLineSeries = (data) => data.line_series.map((item) => ({
        x: parseDateValue(item.x),
        y: item.y
    }));

    const renderChart = (data) => {
        const chartType = data.chart_type || 'candlestick';
        const seriesData = chartType === 'line'
            ? buildLineSeries(data)
            : buildCandleSeries(data);

        if (chart) {
            const currentType = chart.w?.config?.chart?.type;
            if (currentType !== chartType) {
                chart.destroy();
                chart = null;
            }
        }

        if (chart) {
            chart.updateSeries([
                {
                    name: 'Price',
                    data: seriesData
                }
            ], true);
            chart.updateOptions({
                yaxis: {
                    title: {
                        text: `Price (${data.currency_code})`
                    }
                }
            });
            return;
        }

        const options = {
            series: [{
                name: 'Price',
                data: seriesData
            }],
            chart: {
                type: chartType,
                height: 500,
                toolbar: {
                    show: true
                }
            },
            title: {
                text: 'Asset Performance',
                align: 'left'
            },
            xaxis: {
                type: 'datetime',
                title: {
                    text: 'Date'
                }
            },
            yaxis: {
                title: {
                    text: `Price (${data.currency_code})`
                },
                tooltip: {
                    enabled: true
                }
            },
            plotOptions: {
                candlestick: {
                    colors: {
                        upward: '#00B746',
                        downward: '#EF403C'
                    }
                }
            },
            stroke: {
                width: chartType === 'line' ? 2 : 1
            },
            tooltip: {
                enabled: true
            }
        };

        chart = new ApexCharts(document.querySelector("#assetChart"), options);
        chart.render();
    };

    const loadRange = async (range) => {
        if (!baseUrl) {
            return;
        }
        const url = `${baseUrl}?range=${encodeURIComponent(range)}`;
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        renderChart(data);
    };

    rangeButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const range = button.dataset.range || defaultRange;
            setActiveRange(range);
            loadRange(range);
        });
    });

    setActiveRange(defaultRange);
    loadRange(defaultRange);
});