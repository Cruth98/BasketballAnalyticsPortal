import pandas as pd
from pathlib import Path

## Create function to extract practice date from filename
def extract_practice_date(file_name: str):
    """
    Extract the practice date from a YYMMDD filename like '251017.csv'.
    Assumes:
        - First two digits = year (20YY)
        - Next two digits = month
        - Last two digits = day
    """
    stem = Path(file_name).stem  # e.g., "251017"

    if len(stem) == 6 and stem.isdigit():
        yy = int(stem[0:2])
        mm = int(stem[2:4])
        dd = int(stem[4:6])

        year = 2000 + yy

        try:
            return pd.Timestamp(year=year, month=mm, day=dd)
        except ValueError:
            return pd.NaT

    return pd.NaT

## Create function to load all practice data from folder
def load_practice_data(folder_path: str) -> pd.DataFrame:
    """
    Load ALL practice CSV files from the given folder into
    one cumulative DataFrame for the entire season.

    - Drops columns with all NAs
    - Adds only PracticeDate (parsed from filename)
    """
    folder = Path(folder_path)
    practice_files = sorted(folder.glob("*.csv"))

    all_practices = []

    for file_path in practice_files:
        # Read raw CSV
        data = pd.read_csv(file_path)

        # Drop unnecessary columns
        cols_to_drop = ['Timeline','Duration','Start time', 'DudeOfDay', 'PlayCalls', 'Teaching', 'Notes', '2 Cross']
        data = data.drop(columns=cols_to_drop, errors='ignore')

        # Drop columns containing only NA values
        data = data.dropna(axis=1, how="all")

        ## Rename Columns
        data.rename(columns={
                    'Row': 'Team',
                    'Instance number': 'clipID'}, inplace=True)

        # Add derived practice date
        data["PracticeDate"] = extract_practice_date(file_path.name)

        if "Team" in data.columns:
            data["Team"] = data["Team"].astype(str).str.strip()

        # Convert PracticeDate to string for UID (format YYYY-MM-DD)
        data["PracticeDateStr"] = data["PracticeDate"].dt.strftime("%Y-%m-%d")

        # Add UID column: PracticeDate + Team + clipID
        data["UID"] = (
            data["PracticeDateStr"].fillna("UnknownDate") + "_" +
            data["Team"].astype(str) + "_" +
            data["clipID"].astype(str)
        )

        all_practices.append(data)

    if not all_practices:
        return pd.DataFrame()

    # Combine into season-long dataset
    season_data = pd.concat(all_practices, ignore_index=True)

    # Ensure datetime dtype for PracticeDate
    if "PracticeDate" in season_data.columns:
        season_data["PracticeDate"] = pd.to_datetime(
            season_data["PracticeDate"], errors="coerce"
        )

    # Drop helper column
    season_data = season_data.drop(columns=["PracticeDateStr"], errors="ignore")

    # Replace remaining nulls with string "NONE" in object columns only
    object_cols = season_data.select_dtypes(include=["object"]).columns
    season_data[object_cols] = season_data[object_cols].fillna("NONE")

    return season_data

def load_wars_analysis(file_path: str) -> pd.DataFrame:
    """
    Load WARS analysis data from Excel.
    """
    df = pd.read_excel(
        file_path,
        sheet_name="Wars Analysis"
    )
    
    # Create unique Game_War_UID using GameOrder and WarNum
    df['Game.War'] = pd.concat([
        df['GameOrder'].astype(str),
        df['WarNum'].astype(str),
    ], axis=1).agg(".".join, axis=1)

    # Create WarLost & GameLost column
    df['WarLost'] = df['WarWon'].apply(lambda x: 1 if x == 0 else 0)
    df['GameLost'] = df['GameWon'].apply(lambda x: 1 if x == 0 else 0)
    
    # Create WarResult & GameResult columns
    df['WarResult'] = df['WarWon'].apply(lambda x: 'Win' if x == 1 else 'Loss')
    df['GameResult'] = df['GameWon'].apply(lambda x: 'Win' if x == 1 else 'Loss')

    # Create ConfGame & HomeGame categorical columns
    df['ConfGame'] = df['ConfGame'].apply(lambda x: 'Yes' if x == 1 else 'No')
    df['HomeGame'] = df['HomeGame'].apply(lambda x: 'Yes' if x == 1 else 'No')

    ## Set column orders
    desired_order = [
        'GameOrder', 'Opponent', 'ConfGame', 'HomeGame',
        'Half', 'WarNum', 'WarLabel',
        'BU_Score', 'Opp_Score', 'ScoreDiff',
        'WarResult', 'GameResult']
    
    ## Reorder columns
    df = df.reindex(columns=desired_order + [col for col in df.columns if col not in desired_order])

    # Set index as Game.War
    df = df.set_index('Game.War')
        
    return df
