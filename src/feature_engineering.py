import pandas as pd
from pandas import DataFrame
from prometheus_extract import extract_dataset

def transform_dataframe(raw_df: DataFrame) -> DataFrame:
    df = raw_df.copy()

    df['date_hour'] = pd.to_datetime(df['timestamp'], unit='s')

    df['hour'] = df['date_hour'].dt.hour
    df['day_week'] = df['date_hour'].dt.dayofweek
    
    df['cpu_lag_15m'] = df['cpu_usage'].shift(3)
    df['rps_lag_15m'] = df['rps'].shift(3)
    
    df = df.dropna()
    
    return df

if __name__ == "__main__":
    print(transform_dataframe(extract_dataset()))