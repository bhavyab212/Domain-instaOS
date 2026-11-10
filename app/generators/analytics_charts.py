"""Matplotlib 3-panel dark-mode executive dashboard PNG generator."""

import os
from pathlib import Path
from typing import Any
import matplotlib

# Set non-interactive backend before importing pyplot
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_executive_dashboard_png(store: Any, output_dir: Path | str) -> str:
    """Renders a 3-panel dark-mode analytics dashboard showing Stock by SKU, Order Stages, and Prepaid vs COD Revenue."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "instaos_live_dashboard.png"

    # Dark mode color palette
    bg_color = "#0f172a"
    card_color = "#1e293b"
    text_color = "#f8fafc"
    muted_text = "#94a3b8"
    accent_indigo = "#6366f1"
    accent_emerald = "#10b981"
    accent_amber = "#f59e0b"
    accent_rose = "#f43f5e"
    accent_cyan = "#06b6d4"

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5), facecolor=bg_color)
    plt.subplots_adjust(wspace=0.35)

    # -------------------------------------------------------------
    # Panel 1: Live Stock by SKU
    # -------------------------------------------------------------
    ax1.set_facecolor(card_color)
    skus = []
    stock_totals = []
    for sku, prod in store.inventory.items():
        skus.append(f"{prod['name'][:14]}..\n({sku})")
        stock_totals.append(sum(prod["stock"].values()))

    bars1 = ax1.bar(skus, stock_totals, color=accent_indigo, edgecolor="#4338ca", width=0.55)
    ax1.set_title("Live Stock by Product SKU", color=text_color, fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylabel("Available Units", color=muted_text, fontsize=10)
    ax1.tick_params(colors=muted_text, labelsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.15, color="#ffffff")
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.3, f"{int(yval)}", ha="center", va="bottom", color=text_color, fontsize=10, fontweight="bold")
    for spine in ax1.spines.values():
        spine.set_color("#334155")

    # -------------------------------------------------------------
    # Panel 2: Orders by Fulfilment Stage (Donut Chart)
    # -------------------------------------------------------------
    ax2.set_facecolor(card_color)
    stage_counts = {}
    for o in store.orders.values():
        st = o.get("stage", "UNKNOWN")
        stage_counts[st] = stage_counts.get(st, 0) + 1

    if not stage_counts:
        stage_counts = {"NO_ORDERS": 1}

    labels = list(stage_counts.keys())
    counts = list(stage_counts.values())
    pie_colors = [accent_emerald, accent_cyan, accent_indigo, accent_amber, accent_rose][:len(labels)]

    wedges, texts, autotexts = ax2.pie(
        counts,
        labels=labels,
        colors=pie_colors,
        autopct="%1.0f%%",
        startangle=140,
        wedgeprops=dict(width=0.45, edgecolor=bg_color, linewidth=2),
        textprops=dict(color=muted_text, fontsize=9),
    )
    for at in autotexts:
        at.set_color(text_color)
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax2.set_title("Orders by Fulfilment Stage", color=text_color, fontsize=13, fontweight="bold", pad=12)

    # -------------------------------------------------------------
    # Panel 3: Gross Revenue: Prepaid vs COD
    # -------------------------------------------------------------
    ax3.set_facecolor(card_color)
    prepaid_rev = sum(o.get("final_total", 0.0) for o in store.orders.values() if o.get("payment_mode") == "PREPAID" and "ON_HOLD" not in o.get("status", ""))
    cod_rev = sum(o.get("final_total", 0.0) for o in store.orders.values() if o.get("payment_mode") == "COD" and "ON_HOLD" not in o.get("status", ""))

    rev_labels = ["Prepaid (UPI)", "Cash on Delivery (COD)"]
    rev_vals = [prepaid_rev, cod_rev]
    rev_colors = [accent_emerald, accent_amber]

    bars3 = ax3.bar(rev_labels, rev_vals, color=rev_colors, width=0.45, edgecolor="#334155")
    ax3.set_title("Settled Revenue: Prepaid vs COD", color=text_color, fontsize=13, fontweight="bold", pad=12)
    ax3.set_ylabel("Gross Revenue (INR)", color=muted_text, fontsize=10)
    ax3.tick_params(colors=muted_text, labelsize=9)
    ax3.grid(axis="y", linestyle="--", alpha=0.15, color="#ffffff")
    for bar in bars3:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2.0, yval + (max(rev_vals) * 0.02 if max(rev_vals) > 0 else 50), f"₹{yval:,.0f}", ha="center", va="bottom", color=text_color, fontsize=10, fontweight="bold")
    for spine in ax3.spines.values():
        spine.set_color("#334155")

    # Overall Figure Title
    fig.suptitle("InstaOS Executive Operations Dashboard — Nonilion Virtual Office", color=text_color, fontsize=15, fontweight="heavy", y=0.98)

    plt.tight_layout()
    plt.savefig(out_file, dpi=150, facecolor=bg_color, edgecolor="none", bbox_inches="tight")
    plt.close(fig)

    return str(out_file)
