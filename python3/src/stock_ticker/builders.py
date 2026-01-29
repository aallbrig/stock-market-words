"""
Build JSON assets from processed data.
"""
import json
import numpy as np
import pandas as pd
from .config import API_DIR
from .utils import get_today
from .database import get_connection, record_pipeline_step
from .logging_setup import setup_logging

logger = setup_logging()


def build_assets(dry_run=False):
    """Generate optimized trie.json and metadata.json."""
    if dry_run:
        logger.info("DRY RUN: Would build JSON assets")
        conn = get_connection()
        today = get_today()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM daily_metrics 
            WHERE date = ? AND price >= 5.0 AND volume >= 100000 AND market_cap IS NOT NULL
        """, (today,))
        ticker_count = cursor.fetchone()[0]
        conn.close()
        logger.info(f"DRY RUN: Would build from {ticker_count} tickers")
        logger.info(f"DRY RUN: Would calculate 5 strategy scores via percentile ranking")
        logger.info(f"DRY RUN: Would generate trie.json (autocomplete prefix tree)")
        logger.info(f"DRY RUN: Would generate metadata.json (full ticker data + scores)")
        logger.info(f"DRY RUN: Output directory: {API_DIR}")
        return
    
    logger.info("=== Starting Build Phase ===")
    
    conn = get_connection()
    today = get_today()
    
    # Load all tickers with complete data for today
    query = """
        SELECT 
            t.symbol, t.name, t.exchange, t.sector, t.industry,
            dm.price, dm.volume, dm.market_cap, 
            dm.dividend_yield, dm.beta, dm.rsi_14, dm.ma_200, dm.ma_50,
            dm.pe_ratio, dm.forward_pe, dm.price_to_book, dm.peg_ratio,
            dm.enterprise_value, dm.week_52_high, dm.week_52_low,
            dm.avg_volume_10day, dm.short_ratio, dm.short_percent_float,
            dm.debt_to_equity, dm.current_ratio, dm.quick_ratio,
            dm.profit_margin, dm.operating_margin,
            dm.return_on_equity, dm.return_on_assets,
            dm.revenue_growth, dm.earnings_growth,
            dm.target_mean_price, dm.recommendation_mean, dm.num_analyst_opinions,
            dm.shares_outstanding, dm.float_shares
        FROM tickers t
        JOIN daily_metrics dm ON t.symbol = dm.symbol
        WHERE dm.date = ?
        AND dm.price >= 5.0
        AND dm.volume >= 100000
        AND dm.market_cap IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn, params=(today,))
    
    if df.empty:
        # Check if assets already exist
        trie_path = API_DIR / "trie.json"
        metadata_path = API_DIR / "metadata.json"
        
        if trie_path.exists() and metadata_path.exists():
            logger.info("✓ JSON assets already built for today.")
            
            # Get count from metadata.json
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    ticker_count = len(metadata)
                    logger.info(f"  • trie.json: {trie_path}")
                    logger.info(f"  • metadata.json: {metadata_path} ({ticker_count:,} tickers)")
            except:
                logger.info(f"  • Assets exist at {API_DIR}")
        else:
            logger.warning("No tickers found with complete data for today.")
        
        conn.close()
        return
    
    logger.info(f"Building assets from {len(df)} tickers...")
    
    # Calculate strategy scores
    logger.info("Calculating strategy scores...")
    
    # Dividend Daddy: High yield + low volatility
    df['dividend_daddy_raw'] = (
        (df['dividend_yield'].fillna(0) * 100) + 
        (100 - df['beta'].fillna(1).abs() * 50)
    )
    
    # Moon Shot: High growth potential (high beta, oversold RSI)
    df['moon_shot_raw'] = (
        (df['beta'].fillna(0) * 50) + 
        (100 - df['rsi_14'].fillna(50))
    )
    
    # Falling Knife: Oversold + below MA
    df['falling_knife_raw'] = (
        (100 - df['rsi_14'].fillna(50)) + 
        ((df['ma_200'].fillna(df['price']) - df['price']) / df['price'] * 100)
    )
    
    # Over Hyped: Overbought (high RSI)
    df['over_hyped_raw'] = df['rsi_14'].fillna(50)
    
    # Institutional Whale: Large market cap
    df['inst_whale_raw'] = np.log10(df['market_cap'].fillna(1))
    
    # Convert to percentile ranks (1-100)
    score_columns = [
        'dividend_daddy_raw', 'moon_shot_raw', 'falling_knife_raw',
        'over_hyped_raw', 'inst_whale_raw'
    ]
    
    for col in score_columns:
        score_name = col.replace('_raw', '_score')
        df[score_name] = df[col].rank(pct=True) * 100
        df[score_name] = df[score_name].fillna(50).astype(int)
    
    # Save strategy scores to database
    cursor = conn.cursor()
    score_data = []
    
    for _, row in df.iterrows():
        score_data.append((
            row['symbol'], today,
            int(row['dividend_daddy_score']),
            int(row['moon_shot_score']),
            int(row['falling_knife_score']),
            int(row['over_hyped_score']),
            int(row['inst_whale_score'])
        ))
    
    cursor.executemany("""
        INSERT OR REPLACE INTO strategy_scores 
        (symbol, date, dividend_daddy_score, moon_shot_score, 
         falling_knife_score, over_hyped_score, inst_whale_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, score_data)
    conn.commit()
    
    logger.info("✓ Strategy scores saved to database.")
    
    # Build trie.json (prefix tree for autocomplete)
    logger.info("Building trie.json...")
    trie = {}
    
    for _, row in df.iterrows():
        symbol = row['symbol']
        name = row['name']
        
        # Add symbol to trie
        for i in range(1, len(symbol) + 1):
            prefix = symbol[:i].upper()
            if prefix not in trie:
                trie[prefix] = []
            if symbol not in trie[prefix]:
                trie[prefix].append(symbol)
        
        # Add name words to trie
        if pd.notna(name):
            words = name.upper().split()
            for word in words:
                for i in range(1, min(len(word) + 1, 6)):  # Limit prefix length
                    prefix = word[:i]
                    if prefix not in trie:
                        trie[prefix] = []
                    if symbol not in trie[prefix]:
                        trie[prefix].append(symbol)
    
    trie_path = API_DIR / "trie.json"
    with open(trie_path, 'w') as f:
        json.dump(trie, f, separators=(',', ':'))
    
    logger.info(f"✓ trie.json saved ({len(trie)} prefixes)")
    
    # Build metadata.json
    logger.info("Building metadata.json...")
    metadata = {}
    
    for _, row in df.iterrows():
        symbol = row['symbol']
        metadata[symbol] = {
            'name': row['name'],
            'exchange': row['exchange'],
            'sector': row['sector'] if pd.notna(row['sector']) else None,
            'industry': row['industry'] if pd.notna(row['industry']) else None,
            'price': round(float(row['price']), 2),
            'volume': int(row['volume']),
            'marketCap': int(row['market_cap']) if pd.notna(row['market_cap']) else None,
            'dividendYield': round(float(row['dividend_yield'] * 100), 2) if pd.notna(row['dividend_yield']) else None,
            'beta': round(float(row['beta']), 2) if pd.notna(row['beta']) else None,
            'rsi': round(float(row['rsi_14']), 1) if pd.notna(row['rsi_14']) else None,
            'ma200': round(float(row['ma_200']), 2) if pd.notna(row['ma_200']) else None,
            'ma50': round(float(row['ma_50']), 2) if pd.notna(row['ma_50']) else None,
            # Valuation metrics
            'peRatio': round(float(row['pe_ratio']), 2) if pd.notna(row['pe_ratio']) else None,
            'forwardPE': round(float(row['forward_pe']), 2) if pd.notna(row['forward_pe']) else None,
            'priceToBook': round(float(row['price_to_book']), 2) if pd.notna(row['price_to_book']) else None,
            'pegRatio': round(float(row['peg_ratio']), 2) if pd.notna(row['peg_ratio']) else None,
            'enterpriseValue': int(row['enterprise_value']) if pd.notna(row['enterprise_value']) else None,
            # Price range
            'week52High': round(float(row['week_52_high']), 2) if pd.notna(row['week_52_high']) else None,
            'week52Low': round(float(row['week_52_low']), 2) if pd.notna(row['week_52_low']) else None,
            # Volume
            'avgVolume10Day': int(row['avg_volume_10day']) if pd.notna(row['avg_volume_10day']) else None,
            # Short interest
            'shortRatio': round(float(row['short_ratio']), 2) if pd.notna(row['short_ratio']) else None,
            'shortPercentFloat': round(float(row['short_percent_float'] * 100), 2) if pd.notna(row['short_percent_float']) else None,
            # Financial health
            'debtToEquity': round(float(row['debt_to_equity']), 2) if pd.notna(row['debt_to_equity']) else None,
            'currentRatio': round(float(row['current_ratio']), 2) if pd.notna(row['current_ratio']) else None,
            'quickRatio': round(float(row['quick_ratio']), 2) if pd.notna(row['quick_ratio']) else None,
            # Profitability
            'profitMargin': round(float(row['profit_margin'] * 100), 2) if pd.notna(row['profit_margin']) else None,
            'operatingMargin': round(float(row['operating_margin'] * 100), 2) if pd.notna(row['operating_margin']) else None,
            'returnOnEquity': round(float(row['return_on_equity'] * 100), 2) if pd.notna(row['return_on_equity']) else None,
            'returnOnAssets': round(float(row['return_on_assets'] * 100), 2) if pd.notna(row['return_on_assets']) else None,
            # Growth
            'revenueGrowth': round(float(row['revenue_growth'] * 100), 2) if pd.notna(row['revenue_growth']) else None,
            'earningsGrowth': round(float(row['earnings_growth'] * 100), 2) if pd.notna(row['earnings_growth']) else None,
            # Analyst data
            'targetMeanPrice': round(float(row['target_mean_price']), 2) if pd.notna(row['target_mean_price']) else None,
            'recommendationMean': round(float(row['recommendation_mean']), 2) if pd.notna(row['recommendation_mean']) else None,
            'numAnalystOpinions': int(row['num_analyst_opinions']) if pd.notna(row['num_analyst_opinions']) else None,
            # Share data
            'sharesOutstanding': int(row['shares_outstanding']) if pd.notna(row['shares_outstanding']) else None,
            'floatShares': int(row['float_shares']) if pd.notna(row['float_shares']) else None,
            'scores': {
                'dividendDaddy': int(row['dividend_daddy_score']),
                'moonShot': int(row['moon_shot_score']),
                'fallingKnife': int(row['falling_knife_score']),
                'overHyped': int(row['over_hyped_score']),
                'instWhale': int(row['inst_whale_score'])
            }
        }
    
    metadata_path = API_DIR / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, separators=(',', ':'))
    
    logger.info(f"✓ metadata.json saved ({len(metadata)} tickers)")
    logger.info("=== Build Complete ===")
    
    conn.close()
    
    # Record step completion
    record_pipeline_step('build', len(metadata), 'completed', dry_run=False)
