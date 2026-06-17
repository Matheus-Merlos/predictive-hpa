from pandas import DataFrame
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from feature_engineering import transform_dataframe
from prometheus_extract import extract_dataset

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

    predictions = model.predict(X_test)

    mean_error = mean_absolute_error(y_test, predictions)
    print(f"Erro Médio Absoluto: {mean_error:.2f} réplicas de diferença do HPA real.")

    return model

if __name__ == "__main__":
    df_pronto = transform_dataframe(extract_dataset())
    
    train_model(df_pronto)
