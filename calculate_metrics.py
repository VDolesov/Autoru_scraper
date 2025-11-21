import csv
import math
from collections import defaultdict
from pathlib import Path


def load_labeled_data(csv_path: str):
    data = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            relevance = int(row['Релевантность'].strip()) if row['Релевантность'].strip() else 0
            data.append({
                'query': row['Запрос'],
                'title': row['Заголовок'],
                'relevance': relevance,
                'text': row['Текст'],
                'url': row['URL']
            })
    return data


def precision_at_k(relevances, k):
    if len(relevances) < k:
        k = len(relevances)
    return sum(relevances[:k]) / k


def recall_at_k(relevances, total_relevant, k):
    if total_relevant == 0:
        return 0.0
    if len(relevances) < k:
        k = len(relevances)
    return sum(relevances[:k]) / total_relevant


def average_precision(relevances, total_relevant):
    if total_relevant == 0:
        return 0.0

    ap = 0.0
    hit_count = 0

    for i, rel in enumerate(relevances, 1):
        if rel > 0:
            hit_count += 1
            ap += hit_count / i

    return ap / total_relevant


def dcg_at_k(relevances, k):
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], 1):
        dcg += (2 ** rel - 1) / math.log2(i + 1)
    return dcg


def ndcg_at_k(relevances, k):
    dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)
    return dcg / idcg if idcg > 0 else 0.0


def mrr(relevances):
    for i, rel in enumerate(relevances, 1):
        if rel > 0:
            return 1.0 / i
    return 0.0


def main():
    csv_path = "search_results_after_improvements.csv"  # вместо "search_results_for_labeling.csv"

    if not Path(csv_path).exists():
        print(f" Файл {csv_path} не найден")
        return

    print(" Расчет метрик качества поиска...")
    data = load_labeled_data(csv_path)

    query_groups = defaultdict(list)
    for item in data:
        query_groups[item['query']].append(item)

    for query in query_groups:
        query_groups[query].sort(key=lambda x: data.index(x))

    metrics_per_query = {}

    print("\n" + "=" * 80)
    print("МЕТРИКИ ПО ЗАПРОСАМ:")
    print("=" * 80)

    for query, results in query_groups.items():
        relevances = [item['relevance'] for item in results]
        total_relevant = sum(relevances)
        total_docs = len(relevances)

        metrics = {
            'P@1': precision_at_k(relevances, 1),
            'P@3': precision_at_k(relevances, 3),
            'P@5': precision_at_k(relevances, 5),
            'P@10': precision_at_k(relevances, 10),
            'R@10': recall_at_k(relevances, total_relevant, 10),
            'AP': average_precision(relevances, total_relevant),
            'nDCG@5': ndcg_at_k(relevances, 5),
            'nDCG@10': ndcg_at_k(relevances, 10),
            'MRR': mrr(relevances),
            'total_relevant': total_relevant,
            'total_docs': total_docs
        }
        metrics_per_query[query] = metrics

        print(f"\nЗапрос: '{query}'")
        print(
            f"   Точность: P@1={metrics['P@1']:.3f}, P@3={metrics['P@3']:.3f}, P@5={metrics['P@5']:.3f}, P@10={metrics['P@10']:.3f}")
        print(f"   Полнота: R@10={metrics['R@10']:.3f}")
        print(f"   Average Precision: {metrics['AP']:.3f}")
        print(f"   nDCG: @5={metrics['nDCG@5']:.3f}, @10={metrics['nDCG@10']:.3f}")
        print(f"   MRR: {metrics['MRR']:.3f}")
        print(f"   Релевантных: {metrics['total_relevant']}/{metrics['total_docs']}")

    # Усредненные метрики по всем запросам
    print("\n" + "=" * 80)
    print("УСРЕДНЕННЫЕ МЕТРИКИ ПО ВСЕМ ЗАПРОСАМ:")
    print("=" * 80)

    avg_metrics = {
        'P@1': sum(m['P@1'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'P@3': sum(m['P@3'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'P@5': sum(m['P@5'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'P@10': sum(m['P@10'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'R@10': sum(m['R@10'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'MAP': sum(m['AP'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'nDCG@5': sum(m['nDCG@5'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'nDCG@10': sum(m['nDCG@10'] for m in metrics_per_query.values()) / len(metrics_per_query),
        'MRR': sum(m['MRR'] for m in metrics_per_query.values()) / len(metrics_per_query),
    }

    print(f"\nТОЧНОСТЬ (Precision):")
    print(f"   P@1 (первый результат): {avg_metrics['P@1']:.3f}")
    print(f"   P@3 (топ-3): {avg_metrics['P@3']:.3f}")
    print(f"   P@5 (топ-5): {avg_metrics['P@5']:.3f}")
    print(f"   P@10 (топ-10): {avg_metrics['P@10']:.3f}")

    print(f"\nПОЛНОТА (Recall@10): {avg_metrics['R@10']:.3f}")

    print(f"\nСРЕДНЯЯ ТОЧНОСТЬ (MAP): {avg_metrics['MAP']:.3f}")

    print(f"\nКАЧЕСТВО РАНЖИРОВАНИЯ:")
    print(f"   nDCG@5: {avg_metrics['nDCG@5']:.3f}")
    print(f"   nDCG@10: {avg_metrics['nDCG@10']:.3f}")

    print(f"\nMRR (первый релевантный): {avg_metrics['MRR']:.3f}")

    # Анализ проблем
    print("\n" + "=" * 80)
    print("АНАЛИЗ ПРОБЛЕМ:")
    print("=" * 80)

    # Запросы с самой низкой точностью
    worst_queries = sorted(metrics_per_query.items(), key=lambda x: x[1]['P@5'])[:3]
    print(f"\n🔴 ХУДШИЕ ЗАПРОСЫ (по P@5):")
    for query, metrics in worst_queries:
        print(f"   '{query}': P@5={metrics['P@5']:.3f}")

    # Запросы с самой высокой точностью
    best_queries = sorted(metrics_per_query.items(), key=lambda x: x[1]['P@5'], reverse=True)[:3]
    print(f"\n🟢 ЛУЧШИЕ ЗАПРОСЫ (по P@5):")
    for query, metrics in best_queries:
        print(f"   '{query}': P@5={metrics['P@5']:.3f}")

    # Сохраняем метрики в файл
    output_file = "search_metrics_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ ПО КАЧЕСТВУ ПОИСКА\n")
        f.write("=" * 50 + "\n\n")
        f.write("Усредненные метрики:\n")
        for metric, value in avg_metrics.items():
            f.write(f"{metric}: {value:.3f}\n")

        f.write(f"\nВсего запросов: {len(metrics_per_query)}\n")
        f.write(f"Всего документов: {len(data)}\n")
        total_rel = sum(m['total_relevant'] for m in metrics_per_query.values())
        f.write(f"Всего релевантных документов: {total_rel}\n")

    print(f"\nПолный отчет сохранен в: {output_file}")


if __name__ == "__main__":
    main()