$(document).ready(function() {
    // Load filtered ticker data
    $.getJSON('/data/filtered_tickers.json', function(data) {
        renderFilteredTable('filtered-table', data);
    }).fail(function() {
        $('#filtered-table').html('<div class="alert alert-danger">Failed to load filtered ticker data</div>');
    });

    // Load Pass 1 results summary
    $.getJSON('/data/pass1_results.json', function(data) {
        renderSummary('pass1-summary', data);
    }).fail(function() {
        $('#pass1-summary').html('<div class="alert alert-danger">Failed to load Pass 1 summary</div>');
    });
});

function renderSummary(containerId, data) {
    const container = $('#' + containerId);
    
    const summary = `
        <div class="alert alert-success">
            <h5>Pass 1 Results Summary</h5>
            <strong>Generated:</strong> ${new Date(data.generated_at).toLocaleString()}<br>
            <strong>Total Tickers:</strong> ${data.total_tickers.toLocaleString()}<br>
            <strong>With Price Data:</strong> ${data.with_price_data.toLocaleString()}<br>
            <strong>Missing Data:</strong> ${data.missing_data.toLocaleString()}
        </div>
    `;
    
    container.html(summary);
}

function renderFilteredTable(containerId, data) {
    const container = $('#' + containerId);
    
    // Create info section
    const info = `
        <div class="alert alert-info">
            <strong>Generated:</strong> ${new Date(data.generated_at).toLocaleString()}<br>
            <strong>Total Filtered Tickers:</strong> ${data.total_tickers.toLocaleString()}<br>
            <strong>Description:</strong> These tickers passed all filtering rules and are eligible for price extraction.
        </div>
    `;
    
    // Create table with search
    let content = `
        <div class="mb-3">
            <input type="text" id="ticker-search" class="form-control" placeholder="Search by ticker or name...">
        </div>
        <div class="table-responsive">
            <table class="table table-striped table-hover table-sm" id="tickers-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Name</th>
                        <th>Exchange</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Rows (limit to first 500 for initial render)
    const rowsToShow = Math.min(data.tickers.length, 500);
    for (let i = 0; i < rowsToShow; i++) {
        const ticker = data.tickers[i];
        content += `
            <tr>
                <td><strong>${ticker.symbol}</strong></td>
                <td>${ticker.name}</td>
                <td><span class="badge bg-secondary">${ticker.exchange}</span></td>
            </tr>
        `;
    }
    
    content += '</tbody></table></div>';
    
    if (data.tickers.length > 500) {
        content += `<div class="alert alert-warning">Showing first 500 of ${data.tickers.length} tickers. Use search to find specific symbols.</div>`;
    }
    
    container.html(info + content);
    
    // Add search functionality
    $('#ticker-search').on('keyup', function() {
        const searchTerm = $(this).val().toLowerCase();
        $('#tickers-table tbody tr').each(function() {
            const row = $(this);
            const text = row.text().toLowerCase();
            row.toggle(text.indexOf(searchTerm) > -1);
        });
    });
}
