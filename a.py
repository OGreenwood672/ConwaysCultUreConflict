import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np


def create_radar_chart(values, attributes, title="Attribute Radar Chart"):
    if isinstance(values, dict):
        attributes = list(values.keys())
        values = list(values.values())

    num_vars = len(attributes)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Concentric grid rings — subtle gray
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels([], size=0)
    ax.yaxis.grid(True, color="#e0e0e0", linewidth=0.8, linestyle="-")

    # Draw faint value labels on one spoke
    for val in [25, 50, 75, 100]:
        ax.text(
            0,
            val,
            str(val),
            ha="center",
            va="bottom",
            fontsize=7,
            color="#b0b0b0",
            fontfamily="sans-serif",
        )

    # Radial spokes
    ax.xaxis.grid(True, color="#e8e8e8", linewidth=0.6)

    # Filled polygon
    ax.fill(angles_closed, values_closed, color="#5B9BD5", alpha=0.18)
    ax.plot(
        angles_closed,
        values_closed,
        color="#5B9BD5",
        linewidth=2.2,
        solid_capstyle="round",
    )

    # Data point dots
    ax.scatter(
        angles,
        values,
        color="white",
        s=40,
        zorder=5,
        edgecolors="#5B9BD5",
        linewidths=2,
    )

    # Axis labels and value annotations
    ax.set_xticks(angles)
    ax.set_xticklabels([], size=0)

    label_pad = 18
    for i, (angle, attr, val) in enumerate(zip(angles, attributes, values)):
        ax.text(
            angle,
            100 + label_pad,
            attr.upper(),
            ha="center",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#333333",
            fontfamily="sans-serif",
        )
        ax.text(
            angle,
            100 + label_pad + 10,
            f"{val}%",
            ha="center",
            va="center",
            fontsize=8,
            color="#5B9BD5",
            fontfamily="sans-serif",
        )

    # Outer boundary ring
    ax.plot(
        np.linspace(0, 2 * np.pi, 100),
        [100] * 100,
        color="#d0d0d0",
        linewidth=0.8,
    )

    # Title
    fig.text(
        0.5,
        0.93,
        title,
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="#222222",
        fontfamily="sans-serif",
    )

    ax.tick_params(pad=0)
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    return fig, ax


if __name__ == "__main__":
    values = {
        "Aggression": 65,
        "Resources": 80,
        "Commerce": 45,
        "Resilience": 70,
        "Adaptability": 85,
    }

    fig, ax = create_radar_chart(values, None, title="Colony Attributes")
    plt.savefig("radar_chart.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.show()
