"""CPU-only reporting. Never turn detector scores or graph completion into task success."""
from __future__ import annotations


def monitor_report(rows: list[dict]) -> dict:
    """Labels must be independently supplied; unknown truth is not a negative."""
    counted = [r for r in rows if r.get("truth") in {"complete", "incomplete"}]
    fp = sum(r["predicted"] == "complete" and r["truth"] == "incomplete" for r in counted)
    tp = sum(r["predicted"] == "complete" and r["truth"] == "complete" for r in counted)
    positives = sum(r["truth"] == "complete" for r in counted)
    negatives = len(counted)-positives
    return {"labeled_boundaries": len(counted), "unlabeled_boundaries": len(rows)-len(counted),
            "false_completion": fp, "true_completion": tp,
            "false_completion_rate": fp/negatives if negatives else None,
            "recall": tp/positives if positives else None,
            "abstentions": sum(r["predicted"] == "unknown" for r in rows),
            "note": "Correlated boundaries are not independent episodes; do not infer task success."}


def runtime_report(journal) -> dict:
    graph = journal.records("situated_graph")
    monitor = journal.records("situated_monitor")
    identity = journal.records("situated_identity")
    unresolved = {r["invocation_id"] for r in graph if r["event"] == "reserved"}
    unresolved -= {r["invocation_id"] for r in graph if r["event"] == "result"}
    return {"graph_node_receipts": sum(r["event"] == "result" for r in graph),
            "graph_repairs": sum(r["event"] == "repaired" for r in graph),
            "unresolved_nodes": len(unresolved),
            "monitor_windows": len(monitor), "completion_candidates": sum(
                r["verdict"]["status"] == "complete" for r in monitor),
            "identity_updates": len(identity), "semantic_task_success": "external_evaluator_only",
            "neural_inference_cost": "use_existing_usage_journal",
            "duty_cycle": "use_action_compiler.metrics; count_auxiliary_models_separately"}
