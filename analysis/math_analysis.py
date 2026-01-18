#!/usr/bin/env python3
"""Analyze math category trends from arXiv data."""

import sqlite3
import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

# Connect to the database
DB_PATH = Path(__file__).parent.parent / "backend" / "arxiv_trends.db"

def get_math_data():
    """Fetch all math category data."""
    conn = sqlite3.connect(DB_PATH)

    # Get all math categories
    query = """
    SELECT c.id, c.name, pc.year, pc.month, pc.count
    FROM categories c
    JOIN publication_counts pc ON c.id = pc.category_id
    WHERE c.parent_category = 'math'
    ORDER BY c.id, pc.year, pc.month
    """

    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def filter_valid_data(df):
    """Filter out invalid data points (zeros and outliers)."""
    # Group by category and filter
    filtered_dfs = []
    for cat_id, group in df.groupby('id'):
        counts = group['count'].values
        nonzero = counts[counts > 0]
        if len(nonzero) == 0:
            continue
        median = np.median(nonzero)
        threshold = max(5, median * 0.05)
        valid = group[group['count'] >= threshold].copy()
        filtered_dfs.append(valid)

    return pd.concat(filtered_dfs, ignore_index=True)

def calculate_stats(df):
    """Calculate statistics for each category."""
    stats = []

    for cat_id, group in df.groupby('id'):
        group = group.sort_values(['year', 'month'])
        counts = group['count'].values
        name = group['name'].iloc[0]

        if len(counts) < 24:
            continue

        # Long-term growth (first year vs last year)
        first_year = counts[:12]
        last_year = counts[-12:]
        first_avg = np.mean(first_year)
        last_avg = np.mean(last_year)

        if first_avg > 0:
            growth = (last_avg - first_avg) / first_avg * 100
        else:
            growth = 0

        # Total and average
        total = np.sum(counts)
        avg_monthly = np.mean(counts)

        # Volatility (coefficient of variation)
        volatility = np.std(counts) / np.mean(counts) * 100 if np.mean(counts) > 0 else 0

        # Trend consistency (how linear is the growth?)
        x = np.arange(len(counts))
        if len(counts) > 1:
            correlation = np.corrcoef(x, counts)[0, 1]
        else:
            correlation = 0

        # Seasonality detection (variance between months)
        monthly_avgs = []
        for month in range(1, 13):
            month_data = group[group['month'] == month]['count'].values
            if len(month_data) > 0:
                monthly_avgs.append(np.mean(month_data))
        seasonality = np.std(monthly_avgs) / np.mean(monthly_avgs) * 100 if monthly_avgs and np.mean(monthly_avgs) > 0 else 0

        # Recent acceleration (compare growth rate in last year vs first year)
        if len(counts) >= 36:
            mid_year = counts[12:24]
            mid_avg = np.mean(mid_year)
            early_growth = (mid_avg - first_avg) / first_avg * 100 if first_avg > 0 else 0
            recent_growth = (last_avg - mid_avg) / mid_avg * 100 if mid_avg > 0 else 0
            acceleration = recent_growth - early_growth
        else:
            acceleration = 0

        stats.append({
            'id': cat_id,
            'name': name,
            'total_papers': int(total),
            'avg_monthly': round(avg_monthly, 1),
            'growth_pct': round(growth, 1),
            'volatility': round(volatility, 1),
            'trend_linearity': round(correlation, 3),
            'seasonality': round(seasonality, 1),
            'acceleration': round(acceleration, 1),
            'first_year_avg': round(first_avg, 1),
            'last_year_avg': round(last_avg, 1)
        })

    return pd.DataFrame(stats)

def get_monthly_totals(df):
    """Get total math publications per month."""
    monthly = df.groupby(['year', 'month'])['count'].sum().reset_index()
    monthly['date'] = pd.to_datetime(monthly['year'].astype(str) + '-' + monthly['month'].astype(str) + '-01')
    return monthly.sort_values('date')

def analyze_correlations(df):
    """Find correlations between categories."""
    # Pivot to get categories as columns
    pivot = df.pivot_table(index=['year', 'month'], columns='id', values='count', fill_value=0)

    # Calculate correlation matrix
    corr_matrix = pivot.corr()

    # Find strongest positive and negative correlations
    correlations = []
    for i, cat1 in enumerate(corr_matrix.columns):
        for j, cat2 in enumerate(corr_matrix.columns):
            if i < j:  # Only upper triangle
                corr = corr_matrix.loc[cat1, cat2]
                correlations.append({
                    'cat1': cat1,
                    'cat2': cat2,
                    'correlation': round(corr, 3)
                })

    return pd.DataFrame(correlations)

def main():
    print("=" * 80)
    print("ARXIV MATH CATEGORIES - TREND ANALYSIS")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    df = get_math_data()
    df = filter_valid_data(df)

    print(f"Total records: {len(df)}")
    print(f"Categories: {df['id'].nunique()}")
    print(f"Date range: {df['year'].min()}-{df['month'].min():02d} to {df['year'].max()}-{df['month'].max():02d}")

    # Calculate stats
    stats = calculate_stats(df)
    stats = stats.sort_values('growth_pct', ascending=False)

    # Overall math trend
    monthly_totals = get_monthly_totals(df)
    total_first_year = monthly_totals.head(12)['count'].mean()
    total_last_year = monthly_totals.tail(12)['count'].mean()
    overall_growth = (total_last_year - total_first_year) / total_first_year * 100

    print("\n" + "=" * 80)
    print("1. OVERALL MATH PUBLISHING TRENDS")
    print("=" * 80)
    print(f"\nTotal math papers in dataset: {df['count'].sum():,}")
    print(f"Average monthly (2022): {total_first_year:.0f} papers")
    print(f"Average monthly (recent): {total_last_year:.0f} papers")
    print(f"Overall growth: {overall_growth:.1f}%")

    # Mean growth for relative comparison
    mean_growth = stats['growth_pct'].mean()
    print(f"\nMean subcategory growth: {mean_growth:.1f}%")
    print(f"Median subcategory growth: {stats['growth_pct'].median():.1f}%")
    print(f"Std dev of growth: {stats['growth_pct'].std():.1f}%")

    print("\n" + "=" * 80)
    print("2. FASTEST GROWING MATH FIELDS (Top 10)")
    print("=" * 80)
    top_growing = stats.nlargest(10, 'growth_pct')
    for _, row in top_growing.iterrows():
        relative = row['growth_pct'] - mean_growth
        print(f"\n{row['id']}: {row['name']}")
        print(f"  Growth: {row['growth_pct']:+.1f}% ({relative:+.1f}% vs avg)")
        print(f"  Papers: {row['first_year_avg']:.0f}/mo → {row['last_year_avg']:.0f}/mo")
        print(f"  Acceleration: {row['acceleration']:+.1f}% (positive = speeding up)")

    print("\n" + "=" * 80)
    print("3. DECLINING/STAGNANT FIELDS (Bottom 10)")
    print("=" * 80)
    bottom = stats.nsmallest(10, 'growth_pct')
    for _, row in bottom.iterrows():
        relative = row['growth_pct'] - mean_growth
        print(f"\n{row['id']}: {row['name']}")
        print(f"  Growth: {row['growth_pct']:+.1f}% ({relative:+.1f}% vs avg)")
        print(f"  Papers: {row['first_year_avg']:.0f}/mo → {row['last_year_avg']:.0f}/mo")

    print("\n" + "=" * 80)
    print("4. ACCELERATING vs DECELERATING FIELDS")
    print("=" * 80)
    print("\nFields SPEEDING UP (positive acceleration):")
    accelerating = stats[stats['acceleration'] > 10].nlargest(5, 'acceleration')
    for _, row in accelerating.iterrows():
        print(f"  {row['id']}: {row['name']} - acceleration {row['acceleration']:+.1f}%")

    print("\nFields SLOWING DOWN (negative acceleration):")
    decelerating = stats[stats['acceleration'] < -10].nsmallest(5, 'acceleration')
    for _, row in decelerating.iterrows():
        print(f"  {row['id']}: {row['name']} - acceleration {row['acceleration']:+.1f}%")

    print("\n" + "=" * 80)
    print("5. VOLATILITY ANALYSIS")
    print("=" * 80)
    print("\nMost STABLE fields (low volatility, consistent output):")
    stable = stats[stats['total_papers'] > 1000].nsmallest(5, 'volatility')
    for _, row in stable.iterrows():
        print(f"  {row['id']}: {row['name']} - volatility {row['volatility']:.1f}%, linearity {row['trend_linearity']:.2f}")

    print("\nMost VOLATILE fields (high variance):")
    volatile = stats.nlargest(5, 'volatility')
    for _, row in volatile.iterrows():
        print(f"  {row['id']}: {row['name']} - volatility {row['volatility']:.1f}%")

    print("\n" + "=" * 80)
    print("6. SIZE vs GROWTH ANALYSIS")
    print("=" * 80)

    # Large fields
    large_fields = stats[stats['total_papers'] > stats['total_papers'].quantile(0.75)]
    small_fields = stats[stats['total_papers'] < stats['total_papers'].quantile(0.25)]

    print(f"\nLarge fields (>75th percentile in papers) avg growth: {large_fields['growth_pct'].mean():.1f}%")
    print(f"Small fields (<25th percentile) avg growth: {small_fields['growth_pct'].mean():.1f}%")

    print("\nLargest fields and their growth:")
    largest = stats.nlargest(5, 'total_papers')
    for _, row in largest.iterrows():
        relative = row['growth_pct'] - mean_growth
        print(f"  {row['id']}: {row['total_papers']:,} papers, growth {row['growth_pct']:+.1f}% ({relative:+.1f}% vs avg)")

    print("\n" + "=" * 80)
    print("7. CORRELATION ANALYSIS")
    print("=" * 80)

    corr_df = analyze_correlations(df)

    print("\nMost POSITIVELY correlated pairs (rise and fall together):")
    top_pos = corr_df.nlargest(10, 'correlation')
    for _, row in top_pos.iterrows():
        print(f"  {row['cat1']} ↔ {row['cat2']}: r={row['correlation']:.3f}")

    print("\nMost NEGATIVELY correlated pairs (inverse relationship):")
    top_neg = corr_df.nsmallest(5, 'correlation')
    for _, row in top_neg.iterrows():
        if row['correlation'] < 0:
            print(f"  {row['cat1']} ↔ {row['cat2']}: r={row['correlation']:.3f}")

    print("\n" + "=" * 80)
    print("8. INTERESTING PATTERNS & INSIGHTS")
    print("=" * 80)

    # Find fields that buck the trend
    growing_while_small = stats[(stats['growth_pct'] > mean_growth + 20) & (stats['total_papers'] < stats['total_papers'].median())]
    if len(growing_while_small) > 0:
        print("\n📈 EMERGING FIELDS (small but fast-growing):")
        for _, row in growing_while_small.nlargest(5, 'growth_pct').iterrows():
            print(f"  {row['id']}: {row['name']}")
            print(f"    Only {row['avg_monthly']:.0f} papers/mo but {row['growth_pct']:+.1f}% growth")

    # Fields with high growth AND high acceleration
    hot_and_accelerating = stats[(stats['growth_pct'] > mean_growth) & (stats['acceleration'] > 5)]
    if len(hot_and_accelerating) > 0:
        print("\n🔥 HOTTEST TRENDS (above avg growth AND accelerating):")
        for _, row in hot_and_accelerating.nlargest(5, 'growth_pct').iterrows():
            print(f"  {row['id']}: {row['name']}")
            print(f"    Growth: {row['growth_pct']:+.1f}%, Acceleration: {row['acceleration']:+.1f}%")

    # Fields that grew but are now slowing
    grew_but_slowing = stats[(stats['growth_pct'] > 20) & (stats['acceleration'] < -10)]
    if len(grew_but_slowing) > 0:
        print("\n⚠️ COOLING OFF (grew significantly but now slowing):")
        for _, row in grew_but_slowing.iterrows():
            print(f"  {row['id']}: {row['name']}")
            print(f"    Growth: {row['growth_pct']:+.1f}%, but acceleration: {row['acceleration']:+.1f}%")

    # Highly linear growth (very consistent)
    linear_growth = stats[(stats['trend_linearity'] > 0.9) & (stats['growth_pct'] > 10)]
    if len(linear_growth) > 0:
        print("\n📊 STEADY RISERS (very consistent growth trajectory):")
        for _, row in linear_growth.nlargest(5, 'trend_linearity').iterrows():
            print(f"  {row['id']}: {row['name']}")
            print(f"    Linearity: {row['trend_linearity']:.3f}, Growth: {row['growth_pct']:+.1f}%")

    # Seasonality
    high_seasonality = stats[stats['seasonality'] > 15]
    if len(high_seasonality) > 0:
        print("\n📅 SEASONAL PATTERNS (significant monthly variation):")
        for _, row in high_seasonality.nlargest(3, 'seasonality').iterrows():
            print(f"  {row['id']}: {row['name']} - seasonality {row['seasonality']:.1f}%")

    print("\n" + "=" * 80)
    print("9. SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal categories analyzed: {len(stats)}")
    print(f"Categories growing faster than average: {len(stats[stats['growth_pct'] > mean_growth])}")
    print(f"Categories with negative growth: {len(stats[stats['growth_pct'] < 0])}")
    print(f"Categories accelerating: {len(stats[stats['acceleration'] > 5])}")
    print(f"Categories decelerating: {len(stats[stats['acceleration'] < -5])}")

    # Save detailed stats to CSV
    stats.to_csv(Path(__file__).parent / 'math_stats.csv', index=False)
    print(f"\nDetailed stats saved to: analysis/math_stats.csv")

if __name__ == '__main__':
    main()
