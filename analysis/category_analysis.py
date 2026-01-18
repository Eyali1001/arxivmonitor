#!/usr/bin/env python3
"""
Generalized category trend analysis for arXiv data.
Generates detailed reports for any parent category.
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "backend" / "arxiv_trends.db"
OUTPUT_DIR = Path(__file__).parent

# Category display names
CATEGORY_NAMES = {
    'cs': 'Computer Science',
    'math': 'Mathematics',
    'physics': 'Physics',
    'q-bio': 'Quantitative Biology',
    'q-fin': 'Quantitative Finance',
    'stat': 'Statistics',
    'eess': 'Electrical Engineering and Systems Science',
    'econ': 'Economics'
}


def get_category_data(parent_category):
    """Fetch all data for a parent category."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT c.id, c.name, pc.year, pc.month, pc.count
    FROM categories c
    JOIN publication_counts pc ON c.id = pc.category_id
    WHERE c.parent_category = ?
    ORDER BY c.id, pc.year, pc.month
    """
    df = pd.read_sql_query(query, conn, params=(parent_category,))
    conn.close()
    return df


def get_cross_category_data(categories):
    """Fetch data for specific categories across parents."""
    conn = sqlite3.connect(DB_PATH)
    placeholders = ','.join(['?' for _ in categories])
    query = f"""
    SELECT c.id, c.name, pc.year, pc.month, pc.count
    FROM categories c
    JOIN publication_counts pc ON c.id = pc.category_id
    WHERE c.id IN ({placeholders})
    ORDER BY c.id, pc.year, pc.month
    """
    df = pd.read_sql_query(query, conn, params=categories)
    conn.close()
    return df


def filter_valid_data(df):
    """Filter out invalid data points (zeros and outliers)."""
    if df.empty:
        return df
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
    if not filtered_dfs:
        return pd.DataFrame()
    return pd.concat(filtered_dfs, ignore_index=True)


def calculate_stats(df):
    """Calculate statistics for each category."""
    stats = []
    for cat_id, group in df.groupby('id'):
        group = group.sort_values(['year', 'month'])
        counts = group['count'].values
        name = group['name'].iloc[0]

        if len(counts) < 12:
            continue

        # Long-term growth (first year vs last year)
        first_year = counts[:12]
        last_year = counts[-12:] if len(counts) >= 24 else counts[-(len(counts)//2):]
        first_avg = np.mean(first_year)
        last_avg = np.mean(last_year)

        growth = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        # Total and average
        total = np.sum(counts)
        avg_monthly = np.mean(counts)

        # Volatility (coefficient of variation)
        volatility = np.std(counts) / np.mean(counts) * 100 if np.mean(counts) > 0 else 0

        # Trend consistency (how linear is the growth?)
        x = np.arange(len(counts))
        correlation = np.corrcoef(x, counts)[0, 1] if len(counts) > 1 else 0

        # Year-over-year growth
        yearly = group.groupby('year')['count'].sum().to_dict()
        years = sorted(yearly.keys())
        yoy_2023 = ((yearly.get(2023, 0) - yearly.get(2022, 0)) / yearly.get(2022, 1) * 100) if yearly.get(2022, 0) > 0 else 0
        yoy_2024 = ((yearly.get(2024, 0) - yearly.get(2023, 0)) / yearly.get(2023, 1) * 100) if yearly.get(2023, 0) > 0 else 0
        acceleration = yoy_2024 - yoy_2023

        stats.append({
            'id': cat_id,
            'name': name,
            'total_papers': int(total),
            'avg_monthly': round(avg_monthly, 1),
            'growth_pct': round(growth, 1),
            'volatility': round(volatility, 1),
            'trend_linearity': round(correlation, 3) if not np.isnan(correlation) else 0,
            'yoy_2023': round(yoy_2023, 1),
            'yoy_2024': round(yoy_2024, 1),
            'acceleration': round(acceleration, 1),
            'first_year_avg': round(first_avg, 1),
            'last_year_avg': round(last_avg, 1)
        })

    return pd.DataFrame(stats)


def calculate_correlations(df):
    """Calculate correlations between categories."""
    pivot = df.pivot_table(index=['year', 'month'], columns='id', values='count', fill_value=0)
    if pivot.shape[1] < 2:
        return pd.DataFrame()
    corr_matrix = pivot.corr()

    correlations = []
    for i, cat1 in enumerate(corr_matrix.columns):
        for j, cat2 in enumerate(corr_matrix.columns):
            if i < j:
                corr = corr_matrix.loc[cat1, cat2]
                if not np.isnan(corr):
                    correlations.append({
                        'cat1': cat1,
                        'cat2': cat2,
                        'correlation': round(corr, 3)
                    })
    return pd.DataFrame(correlations)


def calculate_market_share(df):
    """Calculate market share changes."""
    yearly_totals = df.groupby('year')['count'].sum()
    share_data = {}

    for cat_id, group in df.groupby('id'):
        yearly = group.groupby('year')['count'].sum()
        share = (yearly / yearly_totals * 100).to_dict()
        if 2022 in share and 2024 in share:
            share_data[cat_id] = {
                'share_2022': round(share[2022], 2),
                'share_2024': round(share[2024], 2),
                'change': round(share[2024] - share[2022], 2)
            }
    return share_data


def generate_report(parent_id, df, stats, correlations, market_share, reference_categories=None):
    """Generate markdown report for a category."""

    parent_name = CATEGORY_NAMES.get(parent_id, parent_id.upper())

    # Overall stats
    total_papers = df['count'].sum()
    monthly_totals = df.groupby(['year', 'month'])['count'].sum()

    # Get first and last year averages
    df_sorted = df.sort_values(['year', 'month'])
    yearly_totals = df.groupby('year')['count'].sum()

    first_year_total = yearly_totals.get(2022, 0) / 12
    last_year_total = yearly_totals.get(2024, 0) / 12
    overall_growth = ((last_year_total - first_year_total) / first_year_total * 100) if first_year_total > 0 else 0

    mean_growth = stats['growth_pct'].mean()
    median_growth = stats['growth_pct'].median()

    report = f"""# arXiv {parent_name} Trends Analysis Report

**Analysis Period:** January 2022 - December 2024
**Total Papers Analyzed:** {total_papers:,}
**Categories Covered:** {len(stats)} subcategories
**Generated:** {datetime.now().strftime('%B %Y')}

---

## Executive Summary

This report analyzes publication trends across all arXiv {parent_name} subcategories over a 3-year period.

---

## 1. Overall {parent_name} Publishing Trends

### Growth Overview

| Metric | Value |
|--------|-------|
| Total papers (2022-2024) | {total_papers:,} |
| Monthly average (2022) | {first_year_total:,.0f} papers |
| Monthly average (2024) | {last_year_total:,.0f} papers |
| **Overall growth** | **{overall_growth:+.1f}%** |

### Distribution of Growth Rates

- **Mean subcategory growth:** {mean_growth:.1f}%
- **Median subcategory growth:** {median_growth:.1f}%
- **Standard deviation:** {stats['growth_pct'].std():.1f}%
- **Categories with above-average growth:** {len(stats[stats['growth_pct'] > mean_growth])} of {len(stats)}
- **Categories with negative growth:** {len(stats[stats['growth_pct'] < 0])}

---

## 2. Fastest Growing Fields

### Top 10 by Growth Rate

| Rank | Category | Field Name | Growth | vs Average |
|------|----------|------------|--------|------------|
"""

    top_growing = stats.nlargest(10, 'growth_pct')
    for i, (_, row) in enumerate(top_growing.iterrows(), 1):
        relative = row['growth_pct'] - mean_growth
        report += f"| {i} | {row['id']} | {row['name']} | {row['growth_pct']:+.1f}% | {relative:+.1f}% |\n"

    report += """
### Analysis of Top Growers

"""
    for _, row in top_growing.head(5).iterrows():
        report += f"""**{row['id']} ({row['name']}): {row['growth_pct']:+.1f}%**
- Monthly average: {row['first_year_avg']:.0f} → {row['last_year_avg']:.0f} papers
- Acceleration: {row['acceleration']:+.1f}% ({"speeding up" if row['acceleration'] > 0 else "slowing down"})
- Volatility: {row['volatility']:.1f}%

"""

    report += """---

## 3. Slowest Growing / Declining Fields

### Bottom 10 by Growth Rate

| Rank | Category | Field Name | Growth | vs Average |
|------|----------|------------|--------|------------|
"""

    bottom = stats.nsmallest(10, 'growth_pct')
    for i, (_, row) in enumerate(bottom.iterrows(), 1):
        relative = row['growth_pct'] - mean_growth
        report += f"| {i} | {row['id']} | {row['name']} | {row['growth_pct']:+.1f}% | {relative:+.1f}% |\n"

    report += """
---

## 4. Market Share Analysis

### Biggest Share Gainers

| Category | Field | 2022 Share | 2024 Share | Change |
|----------|-------|------------|------------|--------|
"""

    sorted_share = sorted(market_share.items(), key=lambda x: x[1]['change'], reverse=True)
    for cat_id, data in sorted_share[:5]:
        name = stats[stats['id'] == cat_id]['name'].values[0] if len(stats[stats['id'] == cat_id]) > 0 else cat_id
        report += f"| {cat_id} | {name} | {data['share_2022']:.2f}% | {data['share_2024']:.2f}% | {data['change']:+.2f}% |\n"

    report += """
### Biggest Share Losers

| Category | Field | 2022 Share | 2024 Share | Change |
|----------|-------|------------|------------|--------|
"""

    for cat_id, data in sorted_share[-5:]:
        name = stats[stats['id'] == cat_id]['name'].values[0] if len(stats[stats['id'] == cat_id]) > 0 else cat_id
        report += f"| {cat_id} | {name} | {data['share_2022']:.2f}% | {data['share_2024']:.2f}% | {data['change']:+.2f}% |\n"

    report += """
---

## 5. Year-over-Year Dynamics

### Fields That Accelerated in 2024

| Category | Field | 2023 Growth | 2024 Growth | Acceleration |
|----------|-------|-------------|-------------|--------------|
"""

    accelerating = stats[stats['acceleration'] > 5].nlargest(10, 'acceleration')
    for _, row in accelerating.iterrows():
        report += f"| {row['id']} | {row['name']} | {row['yoy_2023']:+.1f}% | {row['yoy_2024']:+.1f}% | {row['acceleration']:+.1f}% |\n"

    report += """
### Fields That Decelerated in 2024

| Category | Field | 2023 Growth | 2024 Growth | Deceleration |
|----------|-------|-------------|-------------|--------------|
"""

    decelerating = stats[stats['acceleration'] < -5].nsmallest(10, 'acceleration')
    for _, row in decelerating.iterrows():
        report += f"| {row['id']} | {row['name']} | {row['yoy_2023']:+.1f}% | {row['yoy_2024']:+.1f}% | {row['acceleration']:+.1f}% |\n"

    report += """
---

## 6. Volatility and Stability

### Most Stable Fields

| Category | Field | Volatility | Trend Linearity |
|----------|-------|------------|-----------------|
"""

    stable = stats[stats['total_papers'] > stats['total_papers'].quantile(0.25)].nsmallest(5, 'volatility')
    for _, row in stable.iterrows():
        report += f"| {row['id']} | {row['name']} | {row['volatility']:.1f}% | {row['trend_linearity']:.2f} |\n"

    report += """
### Most Volatile Fields

| Category | Field | Volatility |
|----------|-------|------------|
"""

    volatile = stats.nlargest(5, 'volatility')
    for _, row in volatile.iterrows():
        report += f"| {row['id']} | {row['name']} | {row['volatility']:.1f}% |\n"

    report += """
---

## 7. Largest Fields by Volume

| Rank | Category | Field | Total Papers | Avg Monthly | Growth |
|------|----------|-------|--------------|-------------|--------|
"""

    largest = stats.nlargest(10, 'total_papers')
    for i, (_, row) in enumerate(largest.iterrows(), 1):
        report += f"| {i} | {row['id']} | {row['name']} | {row['total_papers']:,} | {row['avg_monthly']:.0f} | {row['growth_pct']:+.1f}% |\n"

    # Correlations section
    if not correlations.empty and len(correlations) > 0:
        report += """
---

## 8. Internal Correlations

### Most Positively Correlated Pairs

| Field 1 | Field 2 | Correlation |
|---------|---------|-------------|
"""
        top_corr = correlations.nlargest(10, 'correlation')
        for _, row in top_corr.iterrows():
            report += f"| {row['cat1']} | {row['cat2']} | r = {row['correlation']:.3f} |\n"

        report += """
### Least Correlated / Negatively Correlated Pairs

| Field 1 | Field 2 | Correlation |
|---------|---------|-------------|
"""
        bottom_corr = correlations.nsmallest(5, 'correlation')
        for _, row in bottom_corr.iterrows():
            report += f"| {row['cat1']} | {row['cat2']} | r = {row['correlation']:.3f} |\n"

    # Summary statistics
    report += f"""
---

## 9. Summary Statistics

| Metric | Value |
|--------|-------|
| Total subcategories analyzed | {len(stats)} |
| Categories with positive growth | {len(stats[stats['growth_pct'] > 0])} |
| Categories with negative growth | {len(stats[stats['growth_pct'] < 0])} |
| Categories accelerating (2024 vs 2023) | {len(stats[stats['acceleration'] > 5])} |
| Categories decelerating | {len(stats[stats['acceleration'] < -5])} |
| Highest growth | {stats['growth_pct'].max():.1f}% ({stats.loc[stats['growth_pct'].idxmax(), 'id']}) |
| Lowest growth | {stats['growth_pct'].min():.1f}% ({stats.loc[stats['growth_pct'].idxmin(), 'id']}) |

---

## Appendix: Complete Statistics

| Category | Name | Total | Avg/Mo | Growth | YoY 2023 | YoY 2024 | Accel |
|----------|------|-------|--------|--------|----------|----------|-------|
"""

    for _, row in stats.sort_values('growth_pct', ascending=False).iterrows():
        report += f"| {row['id']} | {row['name'][:30]} | {row['total_papers']:,} | {row['avg_monthly']:.0f} | {row['growth_pct']:+.1f}% | {row['yoy_2023']:+.1f}% | {row['yoy_2024']:+.1f}% | {row['acceleration']:+.1f}% |\n"

    report += """
---

*Report generated from arXiv data collected January 2022 - December 2024*
"""

    return report


def analyze_category(parent_id):
    """Run full analysis for a parent category."""
    print(f"\nAnalyzing {parent_id}...")

    # Get data
    df = get_category_data(parent_id)
    if df.empty:
        print(f"  No data found for {parent_id}")
        return None

    df = filter_valid_data(df)
    if df.empty:
        print(f"  No valid data for {parent_id}")
        return None

    print(f"  Records: {len(df)}, Categories: {df['id'].nunique()}")

    # Calculate statistics
    stats = calculate_stats(df)
    if stats.empty:
        print(f"  Could not calculate stats for {parent_id}")
        return None

    correlations = calculate_correlations(df)
    market_share = calculate_market_share(df)

    # Generate report
    report = generate_report(parent_id, df, stats, correlations, market_share)

    # Save report
    output_path = OUTPUT_DIR / f"{parent_id}_trends_report.md"
    with open(output_path, 'w') as f:
        f.write(report)
    print(f"  Report saved: {output_path}")

    # Save stats CSV
    stats.to_csv(OUTPUT_DIR / f"{parent_id}_stats.csv", index=False)

    return stats


def main():
    print("=" * 60)
    print("ARXIV CATEGORY TREND ANALYSIS")
    print("=" * 60)

    # Get all parent categories
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT DISTINCT parent_category
        FROM categories
        WHERE parent_category IS NOT NULL
    """)
    parent_categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\nFound {len(parent_categories)} parent categories")

    # Analyze each category
    all_stats = {}
    for parent_id in parent_categories:
        stats = analyze_category(parent_id)
        if stats is not None:
            all_stats[parent_id] = stats

    print("\n" + "=" * 60)
    print("CROSS-CATEGORY SUMMARY")
    print("=" * 60)

    # Summary across all categories
    for parent_id, stats in all_stats.items():
        parent_name = CATEGORY_NAMES.get(parent_id, parent_id)
        mean_growth = stats['growth_pct'].mean()
        total = stats['total_papers'].sum()
        print(f"\n{parent_name}:")
        print(f"  Total papers: {total:,}")
        print(f"  Mean growth: {mean_growth:.1f}%")
        print(f"  Fastest: {stats.loc[stats['growth_pct'].idxmax(), 'id']} ({stats['growth_pct'].max():.1f}%)")
        print(f"  Slowest: {stats.loc[stats['growth_pct'].idxmin(), 'id']} ({stats['growth_pct'].min():.1f}%)")


if __name__ == '__main__':
    main()
