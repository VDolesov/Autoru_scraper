def compare_metrics():
    metrics_before = {
        'P@5': 0.660, 'P@10': 0.540, 'nDCG@5': 0.680,
        'nDCG@10': 0.746, 'AvgP': 0.693, 'MRR': 0.750
    }

    metrics_after = {
        'P@5': 0.800,
        'P@10': 0.670,
        'nDCG@5': 0.849,
        'nDCG@10': 0.923,
        'AvgP': 0.857,
        'MRR': 1.000
    }

    print(" СРАВНЕНИЕ МЕТРИК ДО И ПОСЛЕ УЛУЧШЕНИЙ")
    print("=" * 65)
    print(f"{'Метрика':<15} {'До':<8} {'После':<8} {'Изменение':<12} {'Рост':<10}")
    print("-" * 65)

    for metric in metrics_before:
        before = metrics_before[metric]
        after = metrics_after[metric]
        change = after - before
        growth_pct = (change / before) * 100 if before > 0 else 0

        print(f"{metric:<15} {before:<8.3f} {after:<8.3f} {change:+.3f} ({growth_pct:+.1f}%)")


if __name__ == "__main__":
    compare_metrics()