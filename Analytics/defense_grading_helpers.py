import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

def load_defense_game_data(file_path: str) -> pd.DataFrame:
    cols_to_keep = ["Action", "DefenseType", "Shot Quality"]

    try:
        df = pd.read_csv(
            file_path,
            usecols=cols_to_keep,
            encoding="utf-8",
            encoding_errors="replace",
        )
    except ValueError as e:
        # Most common: usecols not found (file has different headers)
        raise ValueError(f"Error loading file (columns mismatch): {file_path}\n{e}") from e
    except UnicodeDecodeError as e:
        # If encoding still fails for some reason
        raise ValueError(f"Error loading file (encoding issue): {file_path}\n{e}") from e
    except Exception as e:
        raise ValueError(f"Error loading file: {file_path}\n{e}") from e

    # Normalize
    if "Action" in df.columns:
        df["Action"] = df["Action"].fillna("Foul Drawn")

    # Set opponent from filename (cleaner than storing the full path)
    opponent = os.path.splitext(os.path.basename(file_path))[0]
    df["Opponent"] = opponent

    return df

def transform_df(df):
    df = df.copy()  # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    ## Create 'SQ' column based on 'Shot Quality' values
    df['SQ'] = df['Shot Quality'].apply(lambda x: 0 if 'No Shot' in x else x[-1]).astype(int)
    df['Attempts'] = df['Shot Quality'].apply(lambda x: 0 if 'No Shot' in x else 1).astype(int)

    ## ----------- Create FGM and FGA columns based on 'Action' values -----------
    df['Action'] = df['Action'].astype(str)  # Ensure 'Action' is string type

    # Create 2FGM Mapping -- Action contains '2' or '+2' but NOT '-2'
    df['FGM2'] = df['Action'].apply(lambda x: 1 if ('2' in x or '+2' in x) and '-2' not in x else 0)
    # Create 3FGM Mapping -- Action contains '3' or '+3' but NOT '-3'
    df['FGM3'] = df['Action'].apply(lambda x: 1 if ('3' in x or '+3' in x) and '-3' not in x else 0)
    # Create 2FGA Mapping -- Action contains '2', '+2', or '-2'
    df['FGA2'] = df['Action'].apply(lambda x: 1 if '2' in x or '+2' in x or '-2' in x else 0)
    # Create 3FGA Mapping -- Action contains '3', '+3', or '-3'
    df['FGA3'] = df['Action'].apply(lambda x: 1 if '3' in x or '+3' in x or '-3' in x else 0)

    # Create FGM & FGA columns
    df['FGM'] = df['FGM2'] + df['FGM3']
    df['FGA'] = df['FGA2'] + df['FGA3']

    ## Create Additional Columns for DataFrame
    df['Points'] = df.apply(lambda row: 2 if row['FGM2'] == 1 else (3 if row['FGM3'] == 1 else 0), axis=1) ## Create 'Result' column based on FGM and FGA values
    df['TOV'] = df['Action'].apply(lambda x: 1 if 'Turnover' in x else 0) ## Create 'TOV' column based on 'Action' values
    df['PaintTouch'] = df['Action'].apply(lambda x: x.count('PaintTouch') if 'PaintTouch' in x else 0) ## Count each 'PaintTouch' in 'Action' column
    df['OREB'] = df['Action'].apply(lambda x: 1 if 'OREB' in x else 0) ## Create 'OREB' column based on 'Action' values

    ## Clean 'DefenseType'
    df['DefenseType'] = df['DefenseType'].str.replace(',', ' to', regex=False)

    ## Clean 'Opponent' column to extract team name from file path after 'BU Defense v '
    df['Opponent'] = df['Opponent'].apply(lambda x: x.split('/')[-1].replace('.csv', '').replace('BU Defense v ', ''))
    return df

def aggregate_full_df(df):
    ## Create Aggregated DataFrame by DefenseType
    df = df.groupby(['Opponent','DefenseType']).agg(
        FGM2=('FGM2', 'sum'),
        FGA2=('FGA2', 'sum'),
        FGM3=('FGM3', 'sum'),
        FGA3=('FGA3', 'sum'),
        FGM=('FGM', 'sum'),
        FGA=('FGA', 'sum'),
        Points=('Points', 'sum'),
        TOV=('TOV', 'sum'),
        PaintTouch=('PaintTouch', 'sum'),
        OREB=('OREB', 'sum'),
        SumSQ=('SQ', 'sum'),
        Attempts=('Attempts', 'sum')
    ).sort_values(by='FGA', ascending=False).reset_index()

    df['AvgSQ'] = (df['SumSQ'] / df['Attempts']).round(1).fillna(0)
    # df.drop(columns=['SumSQ'], inplace=True) ## Drop SumSQ after utilizing it for AvgSQ calculation

    return df

def layer_in_metrics(df):
    df = df.copy()
    ## Layer in % metrics
    df['FG%'] = ((df['FGM'] / df['FGA'])*100).round(1).fillna(0)
    df['2FG%'] = ((df['FGM2'] / df['FGA2'])*100).round(1).fillna(0)
    df['3FG%'] = ((df['FGM3'] / df['FGA3'])*100).round(1).fillna(0)
    df['eFG%'] = (((df['FGM2'] + (1.5 * df['FGM3'])) / df['FGA'])*100).round(1).fillna(0)
    df['3PAr'] = ((df['FGA3'] / df['FGA'])*100).round(1).fillna(0)

    ## Add Custom Columns
    df['Possessions'] = df['FGA'] + df['TOV'] - df['OREB']
    df['Possessions'] = df['Possessions'].replace(0, 1)  # Replace 0 possessions with NaN to avoid division by zero


    ## Create Possession Based Metrics
    df['PPA'] = (df['Points'] / df['FGA']).round(1).fillna(0)
    df['PPP'] = (df['Points'] / df['Possessions']).round(1).fillna(0)
    df['DRTG'] = (df['PPP'] * 100).round(1).fillna(0)

    ## Create % of Possession Metrics
    df['OppOREB%'] = ((df['OREB'] / (df['FGA']-df['FGM'])) * 100).round(1).fillna(0)
    df['OppOREB%'] = df['OppOREB%'].replace(np.inf, 100) ## Designed to set rare occurrence of 1 OREB on 0 Missed FG to 100% (Typically from Free Throw instance)
    df['PT%'] = ((df['PaintTouch'] / df['Possessions']) * 100).round(1).fillna(0)
    df['OppTOV%'] = ((df['TOV'] / df['Possessions']) * 100).round(1).fillna(0)
    full_possession_count = df['Possessions'].sum()
    df['Game%'] = ((df['Possessions'] / full_possession_count) * 100).round(1).fillna(0)
    return df

def load_full_season_defense_data(
    folder_path: str = "/Users/mbbfilm/Documents/BasketballAnalyticsPortal/Data/DefenseGrading",
) -> pd.DataFrame:
    full_season_df = pd.DataFrame()

    for file_name in os.listdir(folder_path):
        # 1) Skip hidden files (e.g., .DS_Store) and non-CSV files
        if file_name.startswith("."):
            continue
        if not file_name.lower().endswith(".csv"):
            continue

        file_path = os.path.join(folder_path, file_name)

        # 2) Skip directories (safety)
        if not os.path.isfile(file_path):
            continue

        game_df = load_defense_game_data(file_path)
        game_df = transform_df(game_df)
        game_df = aggregate_full_df(game_df)
        game_df = layer_in_metrics(game_df)

        full_season_df = pd.concat([full_season_df, game_df], ignore_index=True)

    return full_season_df

## ------------------- FILTER SELECTIONS ------------------- ##

def select_opponent(df: pd.DataFrame):
    if "Opponent" not in df.columns:
        return [], df.iloc[0:0].copy()

    available_opponents = sorted(df["Opponent"].dropna().unique())

    selected_opponents = st.multiselect(
        "Select opponents",
        options=available_opponents,
        default=available_opponents,
    )

    if not selected_opponents:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["Opponent"].isin(selected_opponents)].copy()
    return selected_opponents, df_filtered

def select_defense_type(df: pd.DataFrame):
    if "DefenseType" not in df.columns:
        return [], df

    defense_type_options = sorted(df["DefenseType"].dropna().astype(str).unique().tolist())

    selected_defense_types = st.multiselect(
        "Select Defense Types",
        options=defense_type_options,
        default=defense_type_options,
    )

    if not selected_defense_types:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["DefenseType"].isin(selected_defense_types)].copy()
    return selected_defense_types, df_filtered

def render_defense_summary_filtered(df: pd.DataFrame):
    if df.empty:
        st.info("No data to summarize.")
        return
    
    ## Filter by selected opponents
    selected_opponents, df = select_opponent(df)
    selected_defense_types, df = select_defense_type(df)

    total_games = df['Opponent'].nunique()
    total_defense_types = df['DefenseType'].nunique()
    total_possessions = df['Possessions'].sum()
    avg_ppp = df['PPP'].mean()
    avg_drtg = df['DRTG'].mean()
    avg_pt_pct = df['PT%'].mean()
    avg_efg = df['eFG%'].mean()

    st.subheader("Defense Summary")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    col1.metric("Total Games", total_games)
    col2.metric("Total Defense Types", total_defense_types)
    col3.metric("Total Possessions", total_possessions)
    col4.metric("Avg PPP", f"{avg_ppp:.2f}")
    col5.metric("Avg DRTG", f"{avg_drtg:.1f}")
    col6.metric("Avg PT%", f"{avg_pt_pct:.1f}")
    col7.metric("Avg eFG%", f"{avg_efg:.1f}")

    st.subheader("Full Defense Data")
    
    ## Choose columns to display, in order
    display_columns = [
        "Opponent",
        "DefenseType",
        "Possessions",
        'FGM2',
        'FGA2',
        'FGM3',
        'FGA3',
        'FGM',
        'FGA',
        'Points',
        'FG%',
        '2FG%',
        '3FG%',
        'eFG%',
        '3PAr',
        'AvgSQ',
        'TOV',
        'OppTOV%',
        'PaintTouch',
        'PT%',
        'OREB',
        'OppOREB%',
        'PPA',
        "PPP",
        "DRTG",
        "Game%",
    ]
    
    ## Set up Display df
    display_df = df.copy()
    display_df = display_df[display_columns]


    ## Display df in Streamlit
    if not display_df.empty:
        st.dataframe(display_df, use_container_width=True)

    return df

## Create aggregated Defense summary view with filters
def aggregate_by_opponent(df):
    ## Create Aggregated DataFrame by Opponent
    df = df.groupby(['Opponent']).agg(
        FGM2=('FGM2', 'sum'),
        FGA2=('FGA2', 'sum'),
        FGM3=('FGM3', 'sum'),
        FGA3=('FGA3', 'sum'),
        FGM=('FGM', 'sum'),
        FGA=('FGA', 'sum'),
        Points=('Points', 'sum'),
        TOV=('TOV', 'sum'),
        PaintTouch=('PaintTouch', 'sum'),
        OREB=('OREB', 'sum'),
        SumSQ=('SumSQ', 'sum'),
        Attempts=('Attempts', 'sum')
    ).sort_values(by='FGA', ascending=False).reset_index()

    df.set_index('Opponent', inplace=True)
    df = layer_in_metrics(df)
    df['AvgSQ'] = (df['SumSQ'] / df['Attempts']).round(1).fillna(0)

    ## Choose columns to display, in order
    display_columns = [
        "Possessions",
        'FGM2',
        'FGA2',
        'FGM3',
        'FGA3',
        'FGM',
        'FGA',
        'Points',
        'FG%',
        '2FG%',
        '3FG%',
        'eFG%',
        '3PAr',
        'AvgSQ',
        'TOV',
        'OppTOV%',
        'PaintTouch',
        'PT%',
        'OREB',
        'OppOREB%',
        'PPA',
        "PPP",
        "DRTG",
    ]
    
    ## Set up Display df
    df = df[display_columns]

    return df

## Create aggregated Defense summary view with filters
def aggregate_by_defense(df):
    ## Create Aggregated DataFrame by Defense
    df = df.groupby(['DefenseType']).agg(
        FGM2=('FGM2', 'sum'),
        FGA2=('FGA2', 'sum'),
        FGM3=('FGM3', 'sum'),
        FGA3=('FGA3', 'sum'),
        FGM=('FGM', 'sum'),
        FGA=('FGA', 'sum'),
        Points=('Points', 'sum'),
        TOV=('TOV', 'sum'),
        PaintTouch=('PaintTouch', 'sum'),
        OREB=('OREB', 'sum'),
        SumSQ=('SumSQ', 'sum'),
        Attempts=('Attempts', 'sum')
    ).sort_values(by='FGA', ascending=False).reset_index()

    df.set_index('DefenseType', inplace=True)
    df = layer_in_metrics(df)
    df['AvgSQ'] = (df['SumSQ'] / df['Attempts']).round(1).fillna(0)
    df['Poss%'] = ((df['Possessions'] / df['Possessions'].sum()) * 100).round(1).fillna(0)
    ## Choose columns to display, in order
    display_columns = [
        "Possessions",
        'Poss%',
        'FGM2',
        'FGA2',
        'FGM3',
        'FGA3',
        'FGM',
        'FGA',
        'Points',
        'FG%',
        '2FG%',
        '3FG%',
        'eFG%',
        '3PAr',
        'AvgSQ',
        'TOV',
        'OppTOV%',
        'PaintTouch',
        'PT%',
        'OREB',
        'OppOREB%',
        'PPA',
        "PPP",
        "DRTG",
    ]
    
    ## Set up Display df
    df = df[display_columns]

    return df

## Create visual to show aggregated Defense summary view
def create_defense_visual(df: pd.DataFrame, metric='DRTG'):
    if df.empty:
        st.info("No data to display.")
        return

    df = df[metric].sort_values(ascending=False)
    fig = px.bar(df, x=df.index, y=metric, title=f"{metric} by Defense Type")
    st.plotly_chart(fig, use_container_width=True)
    return fig
