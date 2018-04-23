var overview_chart;

$(function() {

    //global HighChart Options
    Highcharts.setOptions({
        chart: {
            backgroundColor: {
                linearGradient: [0, 0, 500, 500],
                stops: [
                    [0, 'rgb(255, 255, 255)'],
                    [1, 'rgb(240, 240, 255)']
                    ]
            },
            borderWidth: 2,
            plotBackgroundColor: 'rgba(255, 255, 255, .9)',
            plotShadow: true,
            plotBorderWidth: 1
        },
        plotOptions: {
            series: {
                colorByPoint: true
            },
            column: {
                dataLabels: {
                    enabled: true,
                    inside: true
                }
            }
        }
    });

    //Chart
    $(document).ready(function() {
        overview_chart = new Highcharts.Chart(chart_id, {
            chart: chart,
            title: title,
            subtitle: subtitle,
            xAxis: xAxis,
            yAxis: yAxis,
            series: series,
            responsive: {
                rules: [{
                    condition: {
                        maxWidth: 500
                    },
                    chartOptions: {
                        legend: {
                            align: 'center',
                            verticalAlign: 'bottom',
                            layout: 'horizontal'
                        },
                        yAxis: {
                            labels: {
                                align: 'left',
                                x: 0,
                                y: -5
                            },
                            title: {
                                text: null
                            }
                        },
                        subtitle: {
                            text: null
                        },
                        credits: {
                            enabled: false
                        }
                    }
                }]
            }
        });
    });
});

//resize Chart on button click
$('#small').click(function () {
    overview_chart.setSize(230,300);
});
$('#large').click(function () {
    overview_chart.setSize(600, 300);
});