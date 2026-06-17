from pandas import DataFrame
import xgboost as xgb
from sklearn.model_selection import train_test_split

def train_model(full_df: DataFrame) -> DataFrame:
    X = full_df[['cpu_usage', 'mem_usage', 'rps', 'hour', 'day_week', 'cpu_lag_15m', 'rps_lag_15m', 'cpu_per_request', 'mem_per_request']]
    y = full_df['replicas']

    X_benchmark, X_test, y_benchmark, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5
    )

    model.fit(X_benchmark, y_benchmark)

    return model

