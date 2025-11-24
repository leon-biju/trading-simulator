document.body.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.target.id === 'chart-loader' && evt.detail.successful) {
        const data = JSON.parse(evt.detail.xhr.responseText);
        console.log('Chart data received:', data);
        
        // Transform data for ApexCharts candlestick format
        const seriesData = data.candlestick_data.map(item => ({
            x: new Date(item.x),
            y: [item.o, item.h, item.l, item.c]
        }));
        
        const options = {
            series: [{
                name: 'Price',
                data: seriesData
            }],
            chart: {
                type: 'candlestick',
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
                    text: 'Price (' + data.currency_code + ')'
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
            tooltip: {
                enabled: true
            }
        };
        
        const chart = new ApexCharts(document.querySelector("#assetChart"), options);
        chart.render();
        
        console.log('Candlestick chart rendered successfully');
    }
});