import pandas as pd
import numpy as np

def load_defense_game_data(file):
    cols_to_keep = ['Action', 'DefenseType', 'Shot Quality']
    df = pd.read_csv(file, usecols=cols_to_keep)
    df['Action'] = df['Action'].fillna('Foul Drawn')
    df['Opponent'] = file
    return df

def transform_df(df):
    df = df.copy()  # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    ## Create 'SQ' column based on 'Shot Quality' values
    df['SQ'] = df['Shot Quality'].apply(lambda x: 0 if 'No Shot' in x else x[-1]).astype(int)

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
    return df

def aggregate_by_defense_per_game(df):
    ## Create Aggregated DataFrame by DefenseType
    df = df.groupby(['Opponent', 'DefenseType']).agg(
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
        AvgSQ=('SQ', 'mean')
    ).sort_values(by='FGA', ascending=False).reset_index()

    return df

def layer_in_metrics(df):
    df = df.copy()
    ## Layer in % metrics
    df['FG%'] = ((df['FGM'] / df['FGA'])*100).round(1).fillna(0)
    df['2FG%'] = ((df['FGM2'] / df['FGA2'])*100).round(1).fillna(0)
    df['3FG%'] = ((df['FGM3'] / df['FGA3'])*100).round(1).fillna(0)
    df['eFG%'] = (((df['FGM2'] + (1.5 * df['FGM3'])) / df['FGA'])*100).round(1).fillna(0)
    df['AvgSQ'] = df['AvgSQ'].round(1)

    ## Add Custom Columns
    df['Possessions'] = df['FGA'] + df['TOV'] - df['OREB']


    ## Create Possession Based Metrics
    df['PPA'] = (df['Points'] / df['FGA']).round(1).fillna(0)
    df['PPP'] = (df['Points'] / df['Possessions']).round(1).fillna(0)
    df['DRTG'] = (df['PPP'] * 100).round(1).fillna(0)

    ## Create % of Possession Metrics
    df['OppOREB%'] = ((df['OREB'] / (df['FGA']-df['FGM'])) * 100).round(1).fillna(0)
    df['OppOREB%'] = df['OppOREB%'].replace(np.inf, 100)
    df['PT%'] = ((df['PaintTouch'] / df['Possessions']) * 100).round(1).fillna(0)
    df['OppTOV%'] = ((df['TOV'] / df['Possessions']) * 100).round(1).fillna(0)
    full_possession_count = df['Possessions'].sum()
    df['Game%'] = ((df['Possessions'] / full_possession_count) * 100).round(1).fillna(0)
    return df

