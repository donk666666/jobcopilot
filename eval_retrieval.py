"""
RAG 检索评估脚本

评估指标：
- Hit Rate@K: 正确答案出现在 Top-K 结果里的比例（越高越好）
- MRR: 第一个正确答案的平均排名倒数（越接近1越好）
- Precision@K: Top-K 结果里相关文档的占比
- Recall@K: 相关文档中被检索到的比例
- OOD Rejection Rate: 知识库外问题被正确拒绝的比例（分数低/无结果）
- Cross-Doc Recall: 跨文档问题的完整召回率
"""

import json
import sys
import os

# 强制 UTF-8 输出，避免 Windows GBK 编码问题
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.rag.retriever import hybrid_search, _vector_search, _keyword_search


def evaluate(dataset_path: str, top_k: int = 5):
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"=" * 60)
    print(f"RAG 检索评估 | 测试集: {len(dataset)} 条 | Top-K: {top_k}")
    print(f"=" * 60)

    in_domain = []       # 知识库内问题
    cross_doc = []       # 跨文档问题（需要多个文档）
    out_of_domain = []   # 知识库外问题（不应检索到结果）
    vague = []           # 口语化/模糊表述

    # 逐条评估
    for i, item in enumerate(dataset):
        question = item["question"]
        relevant = set(item["relevant_docs"])
        is_ood = len(relevant) == 0          # out-of-domain
        is_cross = len(relevant) > 1         # cross-document
        is_vague = len(question) <= 10       # 口语化/模糊

        docs = hybrid_search(question, top_k=top_k)
        retrieved_sources = [d["source"] for d in docs]
        retrieved_scores = [round(d["score"], 3) for d in docs]

        # --- 根据问题类型计算不同的命中标准 ---
        if is_ood:
            # OOD: 最高分低于阈值（0.45）视为正确拒绝
            max_score = max(retrieved_scores) if retrieved_scores else 0
            rejected = max_score < 0.45
            hit = rejected  # "命中" = 正确拒绝了
            rank = None
            precision = 0
            recall = 0
            tag = "OOD"
            detail = f"max_score={max_score:.3f}, rejected={rejected}"
        elif is_cross:
            # 跨文档: 需要所有相关文档都出现在结果里
            matched = relevant & set(retrieved_sources)
            hit = len(matched) >= 1  # 至少命中一个
            rank = None
            for j, src in enumerate(retrieved_sources, start=1):
                if src in relevant and rank is None:
                    rank = j
            retrieved_relevant = len(matched)
            precision = retrieved_relevant / top_k
            recall = min(retrieved_relevant / len(relevant), 1.0)
            full_recall = len(matched) / len(relevant)  # 额外记录
            tag = "CROSS"
            detail = f"retrieved {len(matched)}/{len(relevant)} docs: {sorted(matched)}"
        else:
            # 单文档: 标准评估
            hit = any(src in relevant for src in retrieved_sources)
            rank = None
            for j, src in enumerate(retrieved_sources, start=1):
                if src in relevant:
                    rank = j
                    break
            retrieved_relevant = sum(1 for src in retrieved_sources if src in relevant)
            precision = retrieved_relevant / top_k
            recall = min(retrieved_relevant / len(relevant), 1.0) if relevant else 0
            if is_vague:
                tag = "VAGUE"
            else:
                tag = "IN"
            full_recall = recall
            detail = f""

        result = {
            "question": question,
            "tag": tag,
            "hit": hit,
            "rank": rank,
            "precision": precision,
            "recall": recall,
            "retrieved": retrieved_sources,
            "scores": retrieved_scores,
            "relevant": sorted(relevant),
            "detail": detail,
        }

        if is_ood:
            out_of_domain.append(result)
        elif is_cross:
            cross_doc.append(result)
        elif is_vague:
            vague.append(result)
        else:
            in_domain.append(result)

        # 打印每条结果
        status = "OK" if hit else "!!"
        rank_str = f"Rank({rank})" if rank else "None"
        print(f"\n[{i+1:02d}] [{tag}] {status} {question}")
        print(f"    期望: {sorted(relevant) if relevant else '(知识库外 — 不应匹配)'}")
        print(f"    实际: {retrieved_sources}")
        print(f"    分数: {retrieved_scores}")
        print(f"    Hit={hit}, {rank_str}, P={precision:.2f}, R={recall:.2f}{' ' + detail if detail else ''}")

    # ==================== 汇总指标 ====================
    all_results = in_domain + cross_doc + out_of_domain + vague
    n = len(all_results)

    # 整体指标
    overall_hit = sum(1 for r in all_results if r["hit"]) / n
    overall_mrr = sum(1 / r["rank"] for r in all_results if r["rank"]) / n

    print(f"\n{'=' * 60}")
    print(f"整体汇总")
    print(f"{'=' * 60}")
    print(f"  Hit Rate@{top_k}:  {overall_hit:.1%}  ({int(overall_hit * n)}/{n})")
    print(f"  MRR:              {overall_mrr:.3f}")

    # 分类型指标
    def print_group(title, group):
        if not group:
            return
        m = len(group)
        h = sum(1 for r in group if r["hit"]) / m
        mrr = sum(1 / r["rank"] for r in group if r["rank"]) / m
        avg_p = sum(r["precision"] for r in group) / m
        avg_r = sum(r["recall"] for r in group) / m
        print(f"\n  [{title}] ({m} 条)")
        print(f"    Hit Rate: {h:.1%}  |  MRR: {mrr:.3f}  |  P@{top_k}: {avg_p:.1%}  |  R@{top_k}: {avg_r:.1%}")

    print(f"\n{'=' * 60}")
    print(f"分类型指标")
    print(f"{'=' * 60}")
    print_group("知识库内-单文档", in_domain)
    print_group("知识库内-跨文档", cross_doc)
    print_group("口语化/模糊表述", vague)
    print_group("知识库外(OOD)", out_of_domain)

    # OOD 专项统计
    if out_of_domain:
        ood_correct = sum(1 for r in out_of_domain if r["hit"])
        print(f"\n  OOD 拒绝率: {ood_correct}/{len(out_of_domain)} = {ood_correct/len(out_of_domain):.1%}")
        print(f"  (OOD 问题被正确拒绝 = 检索最高分 < 0.45)")

    # 未命中清单
    missed = [r for r in all_results if not r["hit"]]
    if missed:
        print(f"\n{'=' * 60}")
        print(f"未命中 ({len(missed)}/{n}):")
        print(f"{'=' * 60}")
        for r in missed:
            print(f"  [{r['tag']}] !! {r['question']}")
            print(f"    期望: {r['relevant'] if r['relevant'] else '(OOD)'}  实际: {r['retrieved']}")
            print(f"    分数: {r['scores']}")

    # 向量 vs 关键词 vs 混合 对比
    print(f"\n{'=' * 60}")
    print(f"向量 vs 关键词 vs 混合检索对比（仅知识库内问题）")
    print(f"{'=' * 60}")
    in_domain_all = in_domain + cross_doc + vague
    vec_hits = kw_hits = 0
    for item in in_domain_all:
        relevant = set(item["relevant"])
        vec_src = [d["source"] for d in _vector_search(item["question"], top_k)]
        kw_src = [d["source"] for d in _keyword_search(item["question"], top_k)]
        if any(s in relevant for s in vec_src):
            vec_hits += 1
        if any(s in relevant for s in kw_src):
            kw_hits += 1
    nd = len(in_domain_all)
    print(f"  纯向量检索  Hit Rate@{top_k}: {vec_hits/nd:.1%}" if nd else "  (无数据)")
    print(f"  纯关键词检索 Hit Rate@{top_k}: {kw_hits/nd:.1%}" if nd else "")
    print(f"  混合检索    Hit Rate@{top_k}: {sum(1 for r in in_domain_all if r['hit'])/nd:.1%}" if nd else "")

    return all_results


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "eval_dataset.json"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    evaluate(path, top_k=k)
