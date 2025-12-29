import pandas as pd

def apply_default_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill default labels for reversal, box touch, live drills, possession type, and shot quality.
    """
    df = df.copy()

    # Handle both NaN and the "NONE" filler from the loader
    def _fill(col, default):
        if col in df.columns:
            df[col] = (
                df[col]
                .replace("NONE", pd.NA)
                .fillna(default)
            )

    _fill("Reversal Number", "Reversal 0")
    _fill("Box Touch Number", "Box Touch 0")
    _fill("LiveDrills", "Other")
    _fill("PossessionType", "Other")
    _fill("Shot Quality", "Shot Qual 0")

    return df


def compute_shot_result(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    action = df.get("Action", "Other").fillna("Other").astype(str)
    action = (
        action
        .str.replace("-", "-", regex=False)   # unicode minus
        .str.replace("+", "+", regex=False)  # unicode plus
        .str.replace(r"([+-])\s+(\d)", r"\1\2", regex=True)  # "+ 1" -> "+1"
    )
    df["Action"] = action

    token = (
        df["Action"]
        .str.extract(r"(?<!\d)([+-]?(?:3|2|1))(?!\d)", expand=False)
        .str.replace(r"^\+", "", regex=True)  # "+1/+2/+3" -> "1/2/3"
    )

    shot_result_map = {"3": 3, "2": 2, "1": 1, "-1": -1, "-2": -2, "-3": -3}
    df["ShotResult"] = token.map(shot_result_map).fillna(0).astype(int)

    # Row-level points scored, no negatives
    df["Points"] = df["ShotResult"].clip(lower=0).astype(int)

    return df

def add_shot_and_possession_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EstPPP, FGA/FGM splits, ball/box counts, shot ratings and labels.
    """
    df = df.copy()

    # --- dictionaries ---

    estPPP_map = {2: 2, 3: 3, 0: 0, -2: 0, -3: 0, 1:1, -1:0}

    BallRevCnt_map = {
        "No Ball Reversals": 0,
        "Reversal 0": 0,
        "Reversal 1": 1,
        "Reversal 2": 2,
        "Reversal 3": 3,
        "Reversal 4": 4,
        "Reversal 5": 5,
    }

    BoxTouchCnt_map = {
        "No Box Touches": 0,
        "Box Touch 0": 0,
        "Box Touch 1": 1,
        "Box Touch 2": 2,
        "Box Touch 3": 3,
        "Box Touch 4": 4,
    }

    ShotRating_map = {
        "No Shot": 0,
        "Shot Qual 0": 0,
        "Shot Qual 1": 1,
        "Shot Qual 2": 2,
        "Shot Qual 3": 3,
        "Shot Qual 4": 4,
        "Foul Drawn, Shot Qual 4": 4,
        "Foul Drawn, No Shot": 0,
    }

    shot_labels_dict = {0: "No Shot", 1: "D", 2: "C", 3: "B", 4: "A"}

    box_touch_labels_dict = {
        0: "None",
        1: "One",
        2: "Two",
        3: "Three or More",
        4: "Three or More",
        5: "Three or More",
    }

    ball_rev_labels_dict = {
        0: "None",
        1: "One",
        2: "Two",
        3: "Three or More",
        4: "Three or More",
        5: "Three or More",
    }

    # --- mappings ---

    # Ensure Action exists
    df["Action"] = df.get("Action", "Other").fillna("Other").astype(str)

    # 1) REQUIRE ShotResult to exist (computed earlier in pipeline)
    if "ShotResult" not in df.columns:
        df = compute_shot_result(df)

    # ✅ ADD THIS LINE
    df["Points"] = df["ShotResult"].clip(lower=0).astype(int)

    # 2) Shot / FT derived stats from ShotResult
    df["FTA"] = df["ShotResult"].isin([1, -1]).astype(int)
    df["FTM"] = (df["ShotResult"] == 1).astype(int)

    df["FGA2"] = df["ShotResult"].isin([2, -2]).astype(int)
    df["FGA3"] = df["ShotResult"].isin([3, -3]).astype(int)
    df["FGM2"] = (df["ShotResult"] == 2).astype(int)
    df["FGM3"] = (df["ShotResult"] == 3).astype(int)

    df["FGA"] = df["FGA2"] + df["FGA3"]
    df["FGM"] = df["FGM2"] + df["FGM3"]

    # 3) EstPPP from ShotResult (keeps your existing idea)
    df["EstPPP"] = (
    df["ShotResult"]
    .map(estPPP_map)
    .fillna(0)
    .astype(float)
)

    # 4) ShotRating from Shot Quality (as you already do)
    if "Shot Quality" in df.columns:
        df["ShotRating"] = df["Shot Quality"].map(ShotRating_map)

    # 5) Impute ShotRating (and PossessionType) for FT rows BEFORE filtering/dropping
    is_ft = df["FTA"] == 1

    if "ShotRating" not in df.columns:
        df["ShotRating"] = pd.NA  # ensures needs_ft_impute works safely

    needs_ft_impute = is_ft & (df["ShotRating"].isna() | (df["ShotRating"] == 0))
    df.loc[needs_ft_impute, "ShotRating"] = 4

    if "Shot Quality" in df.columns:
        df.loc[needs_ft_impute, "Shot Quality"] = "Shot Qual 4"

    if "PossessionType" in df.columns:
        df.loc[is_ft, "PossessionType"] = "Special"

    if "Box Touch Number" in df.columns:
        df["BoxTouchCnt"] = df["Box Touch Number"].map(BoxTouchCnt_map).fillna(0)

    if "Reversal Number" in df.columns:
        df["BallRevCnt"] = df["Reversal Number"].map(BallRevCnt_map).fillna(0)

    if "ShotRating" in df.columns:
        df["ShotLabel"] = df["ShotRating"].map(shot_labels_dict)

    if "BoxTouchCnt" in df.columns:
        df["BoxTouchLabel"] = df["BoxTouchCnt"].map(box_touch_labels_dict)

    if "BallRevCnt" in df.columns:
        df["BallRevLabel"] = df["BallRevCnt"].map(ball_rev_labels_dict)

    # Drop rows where ShotRating is missing UNLESS it is a free throw row
    if "ShotRating" in df.columns:
        df = df[~df["ShotRating"].isna() | is_ft]

    return df


def add_fg_metrics_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds FG%_2, FG%_3, and eFG% (0-100 scale) using base shooting columns.
    """
    df = df.copy()

    for col in ["FGM2", "FGA2", "FGM3", "FGA3", "FGM", "FGA", "FTA", "FTM"]:
        if col not in df.columns:
            # If these are missing, we can't compute FG metrics
            return df

    df["FG%_2"] = (df["FGM2"] / df["FGA2"]).replace([float("inf")], pd.NA)
    df["FG%_3"] = (df["FGM3"] / df["FGA3"]).replace([float("inf")], pd.NA)
    df["FT%"] = (df["FTM"] / df["FTA"]).replace([float("inf")], pd.NA)
    df["eFG%"] = ((df["FGM"] + 0.5 * df["FGM3"]) / df["FGA"]).replace(
        [float("inf")], pd.NA
    )

    df["FG%_2"] = (df["FG%_2"] * 100).fillna(0)
    df["FG%_3"] = (df["FG%_3"] * 100).fillna(0)
    df["eFG%"] = (df["eFG%"] * 100).fillna(0)

    return df


def expand_on_court_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encode the 'On Court' column into player columns (0/1).
    """
    df = df.copy()

    if "On Court" not in df.columns:
        return df

    # Fix the "NONE" issue and handle NaNs
    df["On Court"] = df["On Court"].replace("NONE", "").fillna("").astype(str)

    # Split to lists
    on_court_list = df["On Court"].apply(
        lambda x: [p.strip() for p in x.split(",") if p.strip()]
    )

    # Collect all distinct players
    all_players = sorted({player for lineup in on_court_list for player in lineup})

    # Create a column per player
    for player in all_players:
        df[player] = on_court_list.apply(lambda lineup: 1 if player in lineup else 0)

    return df


def set_categorical_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Set ordered categorical types for label columns and ensure ShotRating is int.
    """
    df = df.copy()

    category_orders = {
        "BoxTouchLabel": ["None", "One", "Two", "Three or More"],
        "BallRevLabel": ["None", "One", "Two", "Three or More"],
        "ShotLabel": ["No Shot", "D", "C", "B", "A"],
    }

    for col, cats in category_orders.items():
        if col in df.columns:
            df[col] = pd.Categorical(df[col], categories=cats, ordered=True)

    if "ShotRating" in df.columns:
        df["ShotRating"] = pd.to_numeric(df["ShotRating"], errors="coerce").fillna(0).astype(int)

    return df

## Function to clean duplicate labels in key columns
def clean_duplicate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean duplicate comma-separated labels in key columns.
    E.g. 'Half Court, Half Court' -> 'Half Court'
    """
    dedupe_cols = ["PossessionType", "LiveDrills"]

    for col in dedupe_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.split(",")
                .str[0]
                .str.strip()
            )

    return df

def add_player_stats_from_action(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create one-hot style player stat columns from the Action column,
    but ONLY for player rows where Team starts with '#'.

    - AST     : 'Assist' (but NOT 'Cut Assist')
    - CutAST  : 'Cut Assist'
    - CutFG   : 'Cut FG'
    - TOV     : 'Turnover'
    - STL     : 'Steal'
    - BLK     : 'Block' / 'Blk'
    - DEF     : 'Deflection'
    - OREB    : 'Offensive Rebound'
    - DREB    : 'Defensive Rebound'
    - Crash   : 'Crash attempt at OREB'
    - No Crash: 'No Crash attempt at OREB'
    """
    # Player rows = Team value starts with '#'
    team_str = df["Team"].astype(str)
    player_mask = team_str.str.startswith("#")

    # Ensure these stat columns exist and start at 0
    stat_cols = ["AST", "CutAST", "CutFG", "TOV", "STL", "BLK", "DEFL", "OREB", "DREB", "OREB OPP", "Crash", "No Crash"]
    for col in stat_cols:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = df[col].fillna(0)

    # Work only on player rows with non-null Action
    actions = df.loc[player_mask, "Action"].astype(str).str.strip()

    # --- Assist variants ---
    cut_ast_mask = actions.str.contains("Cut Assist", case=False, na=False)

    # Plain Assist = contains 'Assist' but is NOT a 'Cut Assist'
    ast_mask = (~cut_ast_mask) & actions.str.contains("Assist", case=False, na=False)

    # --- Cut FG ---
    cut_fg_mask = actions.str.contains("Cut FG", case=False, na=False)

    # --- offensive rebounds ---
    oreb_mask = actions.str.contains("O REB", case=False, na=False)

    # --- defensive rebounds ---
    dreb_mask = actions.str.contains("D REB", case=False, na=False)

    # --- Turnovers / Steals / Blocks / Deflections ---
    tov_mask = actions.str.contains("Turnover", case=False, na=False)
    stl_mask = actions.str.contains("Steal", case=False, na=False)
    blk_mask = actions.str.contains("Block", case=False, na=False)
    def_mask = actions.str.contains("Deflection", case=False, na=False)

    # Crash & No Crash
    no_crash_mask = actions.str.contains("No Crash", case=False, na=False)
    crash_mask = (~no_crash_mask) & actions.str.contains("Crash", case=False, na=False)


    # Assign stats
    df.loc[player_mask & ast_mask,     "AST"]    = 1
    df.loc[player_mask & cut_ast_mask, "CutAST"] = 1
    df.loc[player_mask & cut_fg_mask,  "CutFG"]  = 1
    df.loc[player_mask & tov_mask,     "TOV"]    = 1
    df.loc[player_mask & stl_mask,     "STL"]    = 1
    df.loc[player_mask & blk_mask,     "BLK"]    = 1
    df.loc[player_mask & def_mask,     "DEFL"]   = 1
    df.loc[player_mask & oreb_mask,    "OREB"]   = 1
    df.loc[player_mask & dreb_mask,    "DREB"]   = 1
    df.loc[player_mask & crash_mask,   "Crash"]  = 1
    df.loc[player_mask & no_crash_mask, "No Crash"] = 1

    return df

## Remove 'Junk' PossessionType && 'Other' PossessionType rows
def drop_non_actionable_possessions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove possessions that should never be user-facing, such as 'Junk' PossessionType or 'Other' LiveDrills/PossessionType.
    """
    df = df.copy()

    if "PossessionType" in df.columns:
        df = df[~df["PossessionType"].isin(["Junk", "Other"])]

    if "LiveDrills" in df.columns:
        df = df[df["LiveDrills"] != "Other"]

    return df

## MAIN FUNCTION TO PREPARE PRACTICE DATAFRAME ##
def prepare_practice_base(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master row-level transformation pipeline for practice possessions.
    This is what get_practice_data() should call after loading.
    """
    return (
        df
        .pipe(apply_default_labels)
        .pipe(clean_duplicate_labels)
        .pipe(drop_non_actionable_possessions)
        .pipe(compute_shot_result)
        .pipe(add_shot_and_possession_metrics)
        .pipe(add_fg_metrics_to_df)
        .pipe(expand_on_court_columns)
        .pipe(add_player_stats_from_action)
        .pipe(set_categorical_types)
    )