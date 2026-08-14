from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.operators.sampling.lhs import LHS
from pymoo.termination.default import DefaultMultiObjectiveTermination

from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "best_ann_model.h5"
SCALER_PATH = BASE_DIR / "scaler.pkl"

# Load the trained model
model_1 = load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

material_names = [
    "Cement content",
    "Water/Binder",
    "Fine  Aggregate",
    "Course Aggregate",
    "Fly Ash",
    "Silica fume",
    "Blast furnace slag",
    "Plasticizer"
]


# Display names

display_names = [
    "Cement content",
    "Water/Binder",
    "Fine Aggregate",
    "Coarse Aggregate",
    "Fly Ash",
    "Silica fume",
    "Blast furnace slag",
    "Plasticizer"
]


# =========================================================
# PRACTICAL BOUNDS
# =========================================================

bounds = {
    "Cement content": (300, 500),
    "Water/Binder": (0.25, 0.50),
    "Fine  Aggregate": (650, 1100),
    "Course Aggregate": (700, 1100),
    "Fly Ash": (0, 150),
    "Silica fume": (0, 40),
    "Blast furnace slag": (0, 180),
    "Plasticizer": (0, 8)
}

lower_bounds = np.array([v[0] for v in bounds.values()])
upper_bounds = np.array([v[1] for v in bounds.values()])


# =========================================================
# GRADE LIST
# =========================================================

grades = [f"M{g}" for g in range(20, 85, 5)]


# =========================================================
# TARGET STRENGTH
# =========================================================

def compute_target_strength(grade_label, std_dev):
    f_ck = int(grade_label[1:])
    t = 1.65
    return f_ck + t * std_dev


# =========================================================
# MULTI OBJECTIVE PROBLEM
# =========================================================

class ConcreteMixOptimization(Problem):

    def __init__(
        self,
        strength_min,
        strength_max,
        cost_factors,
        co2_factors,
        densities
    ):

        self.strength_min = strength_min
        self.strength_max = strength_max
        self.cost_factors = cost_factors
        self.co2_factors = co2_factors
        self.densities = densities

        super().__init__(
            n_var=8,
            n_obj=3,
            n_constr=7,
            xl=lower_bounds,
            xu=upper_bounds
        )


    def _evaluate(self, X, out, *args, **kwargs):

        df = pd.DataFrame(X, columns=material_names)

        # ==========================================
        # MODEL PREDICTION
        # ==========================================

        X_scaled = scaler.transform(df)
        strength = model_1.predict(X_scaled).flatten()


        # ==========================================
        # COST
        # ==========================================

        cost = np.sum(df.values * self.cost_factors, axis=1)


        # ==========================================
        # CO2
        # ==========================================

        co2 = np.sum(df.values * self.co2_factors, axis=1)


        # ==========================================
        # VOLUME
        # ==========================================

        volume = np.sum(df.values / self.densities, axis=1)


        # ==========================================
        # BINDER CALCULATIONS
        # ==========================================

        cement = df["Cement content"].values
        flyash = df["Fly Ash"].values
        silica = df["Silica fume"].values
        slag = df["Blast furnace slag"].values

        binder = cement + flyash + silica + slag


        # ==========================================
        # REPLACEMENT RATIOS
        # ==========================================

        flyash_ratio = flyash / binder
        silica_ratio = silica / binder
        slag_ratio = slag / binder


        # ==========================================
        # OBJECTIVE NORMALIZATION
        # ==========================================

        strength_norm = strength / 100.0
        cost_norm = cost / 10000.0
        co2_norm = co2 / 1000.0


        # ==========================================
        # OBJECTIVES
        # ==========================================

        out["F"] = np.column_stack([
            -strength_norm,
            cost_norm,
            co2_norm
        ])


        # ==========================================
        # CONSTRAINTS
        # ==========================================

        g1 = np.abs(volume - 1.0) - 0.03

        g2 = self.strength_min - strength
        g3 = strength - self.strength_max

        # Practical replacement constraints
        g4 = flyash_ratio - 0.35
        g5 = silica_ratio - 0.12
        g6 = slag_ratio - 0.50

        # Minimum total binder
        g7 = 380 - binder


        out["G"] = np.column_stack([
            g1,
            g2,
            g3,
            g4,
            g5,
            g6,
            g7
        ])


# =========================================================
# FLASK API COMPATIBILITY WRAPPER
# =========================================================

def optimise(payload):
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required.")

    grade = str(payload.get("grade", ""))
    if grade not in {f"M{number}" for number in range(40, 121, 10)}:
        raise ValueError("grade must be between M40 and M120.")

    try:
        std_dev = float(payload.get("stdDev", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("stdDev must be a number.") from error
    if std_dev < 0:
        raise ValueError("stdDev cannot be negative.")

    material_names_flat = ["cement", "water", "fine", "coarse", "flyAsh", "silica", "slag", "plastic"]
    cost_factors = []
    co2_factors = []
    densities = []

    for material in material_names_flat:
        for suffix, target_list in (("INR", cost_factors), ("CO2", co2_factors), ("KG", densities)):
            key = f"{material}{suffix}"
            if key not in payload:
                raise ValueError(f"{key} is required.")
            try:
                value = float(payload[key])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{key} must be a number.") from error
            if value < 0:
                raise ValueError(f"{key} cannot be negative.")
            target_list.append(value)

    target_strength = compute_target_strength(grade, std_dev)
    top, fig = run_optimization_with_grade(grade, std_dev, *(cost_factors + co2_factors + densities))

    if isinstance(top, str):
        raise ValueError(top)

    if top is None or top.empty:
        raise ValueError("No feasible mix designs found.")

    plt.close(fig)

    solutions = [
        {
            "strength": round(float(row["Strength"]), 2),
            "cost": round(float(row["Cost"]), 2),
            "co2": round(float(row["CO2"]), 2),
        }
        for _, row in top.iterrows()
    ]

    return {
        "targetStrength": round(float(target_strength), 2),
        "solutions": solutions,
    }


# =========================================================
# RUN OPTIMIZATION
# =========================================================

def run_optimization_with_grade(grade, std_dev, *args):

    # ==========================================
    # TARGET STRENGTH
    # ==========================================

    f_target = compute_target_strength(grade, std_dev)

    # Wider practical range
    str_min = f_target - 5
    str_max = f_target + 5


    args = np.array(args).astype(float)

    cost_factors = args[0:8]
    co2_factors = args[8:16]
    densities = args[16:24]


    # ==========================================
    # PROBLEM DEFINITION
    # ==========================================

    problem = ConcreteMixOptimization(
        str_min,
        str_max,
        cost_factors,
        co2_factors,
        densities
    )


    # ==========================================
    # NSGA-II
    # ==========================================

    algorithm = NSGA2(
        pop_size=400,
        sampling=LHS()
    )


    termination = DefaultMultiObjectiveTermination(
        n_max_gen=300
    )


    res = minimize(
        problem,
        algorithm,
        termination,
        verbose=False,
        seed=1
    )


    # ==========================================
    # CHECK RESULTS
    # ==========================================

    if res.F is None:
        return "❌ No feasible solutions found.", None


    # ==========================================
    # DATAFRAME
    # ==========================================

    df = pd.DataFrame(res.X, columns=material_names)


    # Recover actual objectives
    df["Strength"] = -res.F[:, 0] * 100
    df["Cost"] = res.F[:, 1] * 10000
    df["CO2"] = res.F[:, 2] * 1000


    # ==========================================
    # VOLUME CHECK
    # ==========================================

    df["Volume"] = np.sum(
        df[material_names].values / densities,
        axis=1
    )


    # ==========================================
    # FILTER FEASIBLE
    # ==========================================

    df = df[
        (df["Volume"].between(0.97, 1.03)) &
        (df["Strength"].between(str_min, str_max))
    ]


    if df.empty:
        return "❌ No feasible mix designs found.", None


    # ==========================================
    # REMOVE DUPLICATES
    # ==========================================

    df = df.drop_duplicates(subset=["Cost", "CO2"])


    # ==========================================
    # REPRESENTATIVE PARETO SOLUTIONS
    # ==========================================

    low_cost = df.nsmallest(3, "Cost")
    low_co2 = df.nsmallest(3, "CO2")
    high_strength = df.nlargest(3, "Strength")


    # Balanced solution
    df["Score"] = (
        (df["Strength"] / df["Strength"].max())
        - (df["Cost"] / df["Cost"].max())
        - (df["CO2"] / df["CO2"].max())
    )

    balanced = df.nlargest(3, "Score")


    top = pd.concat([
        low_cost,
        low_co2,
        high_strength,
        balanced
    ])


    top = top.drop_duplicates().round(2)


    # ==========================================
    # PARETO PLOT
    # ==========================================

    fig, ax = plt.subplots(figsize=(9, 6))

    scatter = ax.scatter(
        df["Cost"],
        df["CO2"],
        c=df["Strength"],
        cmap="viridis",
        alpha=0.8,
        s=45
    )


    cbar = plt.colorbar(scatter)
    cbar.set_label("Strength (MPa)")


    ax.set_xlabel("Cost (INR)")
    ax.set_ylabel("CO₂ Emissions (kg)")
    ax.set_title("NSGA-II Pareto Front")

    plt.grid(True)


    return top, fig

