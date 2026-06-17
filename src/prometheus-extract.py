import pandas as pd
from pandas import DataFrame
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
from datetime import datetime, timedelta
from config import Config

def search_timeseries_chunked(prometheus_connection: PrometheusConnect, query: str, start_time: datetime, end_time: datetime, step: str, chunk_days: int = 1):
    df_list = []
    current_start = start_time

    while current_start < end_time:
        current_end = min(current_start + timedelta(days=chunk_days), end_time)

        result = prometheus_connection.custom_query_range(
            query=query,
            start_time=current_start,
            end_time=current_end,
            step=step
        )

        if result:
            df_metric = MetricRangeDataFrame(result)
            df_metric = df_metric.reset_index()
            df_metric = df_metric[['timestamp', 'value']]
            df_metric['value'] = pd.to_numeric(df_metric['value'])
            df_metric['timestamp'] = df_metric['timestamp'].dt.floor('s')
            df_list.append(df_metric)
        
        current_start = current_end

    if not df_list:
        return DataFrame(columns=['timestamp', 'value'])

    df_final_metric = pd.concat(df_list, ignore_index=True)
    return df_final_metric

def extract_dataset():
    config = Config()
    prometheus_connection = PrometheusConnect(url=config.prometheus_url, disable_ssl=(not config.prometheus_secure_connection))

    end_time: datetime | None = parse_datetime('now')
    start_time = end_time - timedelta(days=30)
    step = "1m"

    namespace="production"
    app_name="production-green-lms"

    queries = {
        'cpu_usage': f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod=~"{app_name}.*"}}[5m]))', 
        'mem_usage': f'sum(container_memory_working_set_bytes{{namespace="{namespace}", pod=~"{app_name}.*"}})',
        'rps': f'sum(rate(nginx_ingress_controller_requests{{namespace="{namespace}", service=~".*{app_name}.*"}}[5m]))',
        'replicas': f'kube_deployment_spec_replicas{{namespace="{namespace}", deployment=~".*{app_name}.*"}}'
    }

    dataframes: list[DataFrame] = []

    for column_name, query in queries.items():
        df = search_timeseries_chunked(prometheus_connection, query, start_time, end_time, step)

        df = df.drop_duplicates(subset=['timestamp'])

        df = df.rename(columns={'value': column_name})
        dataframes.append(df)

    final_df = dataframes[0]
    for df in dataframes[1:]:
        final_df = pd.merge(final_df, df, on='timestamp', how='outer')

    final_df = final_df.sort_values('timestamp').reset_index(drop=True)
    final_df = final_df.ffill()
    final_df = final_df.dropna()

    print(final_df)

if __name__ == "__main__":
    extract_dataset()