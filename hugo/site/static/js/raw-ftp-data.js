$(document).ready(function() {
    // Load NASDAQ data
    $.getJSON('/data/raw_nasdaq.json', function(data) {
        renderTable('nasdaq-table', data);
    }).fail(function() {
        $('#nasdaq-table').html('<div class="alert alert-danger">Failed to load NASDAQ data</div>');
    });

    // Load Other Exchanges data
    $.getJSON('/data/raw_otherlisted.json', function(data) {
        renderTable('otherlisted-table', data);
    }).fail(function() {
        $('#otherlisted-table').html('<div class="alert alert-danger">Failed to load Other Exchanges data</div>');
    });
});

function renderTable(containerId, data) {
    const container = $('#' + containerId);
    
    // Create info section
    const info = `
        <div class="alert alert-info">
            <strong>Source:</strong> ${data.source}<br>
            <strong>File:</strong> ${data.file}<br>
            <strong>Downloaded:</strong> ${new Date(data.downloaded_at).toLocaleString()}<br>
            <strong>Total Rows:</strong> ${data.total_rows.toLocaleString()}
        </div>
    `;
    
    // Create table
    let table = '<div class="table-responsive"><table class="table table-striped table-hover table-sm"><thead><tr>';
    
    // Headers
    data.columns.forEach(col => {
        table += `<th>${col}</th>`;
    });
    table += '</tr></thead><tbody>';
    
    // Rows (limit to first 100 for performance)
    const rowsToShow = Math.min(data.data.length, 100);
    for (let i = 0; i < rowsToShow; i++) {
        const row = data.data[i];
        table += '<tr>';
        data.columns.forEach(col => {
            const value = row[col] || '';
            table += `<td>${value}</td>`;
        });
        table += '</tr>';
    }
    
    table += '</tbody></table></div>';
    
    if (data.data.length > 100) {
        table += `<div class="alert alert-warning">Showing first 100 of ${data.data.length} rows</div>`;
    }
    
    container.html(info + table);
}
