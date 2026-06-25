import pandas as pd
from pandas import DataFrame

def transform_dataframe(raw_df: DataFrame, is_training: bool = False) -> DataFrame:
    df = raw_df.copy()

    df['date_hour'] = pd.to_datetime(df['timestamp'], unit='s')

    df['hour'] = df['date_hour'].dt.hour
    df['day_week'] = df['date_hour'].dt.dayofweek
    
    df['cpu_lag_15m'] = df['cpu_usage'].shift(15)
    df['rps_lag_15m'] = df['rps'].shift(15)

    df['cpu_per_request'] = df['cpu_usage'] / (df['rps'] + 1e-9)
    df['mem_per_request'] = df['mem_usage'] / (df['rps'] + 1e-9)
    
    df = df.dropna(subset=['cpu_lag_15m', 'rps_lag_15m'])

    if is_training:
        df['target_cpu_15m_ahead'] = df['cpu_usage'].shift(-15)
        df = df.dropna(subset=['target_cpu_15m_ahead'])
    
    return df
