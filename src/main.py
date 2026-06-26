import logging as logger
from datetime import datetime
from xgboost import XGBRegressor
from sklearn.exceptions import NotFittedError
import time
import math

from database import DuckDBConnection
from prometheus_extract import extract_dataset, extract_recent_window, get_pod_resource_requests
from feature_engineering import transform_dataframe
from predictor import train_model
from resource_discovery import discover_resources_by_labels
from config import Config

cfg = Config()

def calculate_reactive_hpa(cpu_usage_total, mem_usage_total, current_replicas, pod_cpu_req, pod_mem_req):
    current_replicas_safe = max(current_replicas, 1)
    replicas_from_cpu = 0
    replicas_from_mem = 0

    if cfg.reactive_hpa_target_cpu_utilization_percentage is not None:
        cpu_per_pod = cpu_usage_total / current_replicas_safe
        desired_cpu_value = pod_cpu_req * float(cfg.reactive_hpa_target_cpu_utilization_percentage)
        replicas_from_cpu = math.ceil(current_replicas_safe * (cpu_per_pod / desired_cpu_value))

    if cfg.reactive_hpa_target_mem_utilization_percentage is not None:
        mem_per_pod = mem_usage_total / current_replicas_safe
        desired_mem_value = pod_mem_req * float(cfg.reactive_hpa_target_mem_utilization_percentage)
        replicas_from_mem = math.ceil(current_replicas_safe * (mem_per_pod / desired_mem_value))

    desired_replicas = max(replicas_from_cpu, replicas_from_mem)
    desired_replicas = max(cfg.reactive_hpa_min_replicas, desired_replicas)
    desired_replicas = min(cfg.reactive_hpa_max_replicas, desired_replicas)

    return desired_replicas

def shadow_mode_controller():
    logger.info('Initializing Predictive-HPA Shadow Mode Controller...')

    logger.info('Fetching kubernetes deployment and service...')
    service_name, deployment_name = discover_resources_by_labels()

    logger.info('Fetching Pod Resource limits from Prometheus...')
    pod_cpu_req, pod_mem_req = get_pod_resource_requests(cfg.namespace, deployment_name)
    logger.info(f'Pod Capacity locked at: CPU={pod_cpu_req} Cores, Mem={pod_mem_req:.2f} GB')

    with DuckDBConnection(cfg.duckdb_file_path) as data:
        logger.info('Gathering all available data on prometheus...')
        history_df = extract_dataset(cfg.namespace, deployment_name, service_name)

        if not history_df.empty:
            data.append_metric(history_df)
            logger.debug('Successfully written data on database.')
        else:
            logger.debug('No data was found.')

        trained_today = False
        model = XGBRegressor()
        days_history = data.get_days_count()
        if days_history >= 7:
            logger.info(f'{days_history} days detected. Forcing initial training...')
            all_data = data.get_all_historical_data()

            model = train_model(transform_dataframe(all_data, is_training=True))
        else:
            logger.info(f'Warmup mode active. Waiting history ({days_history}/7 days)')

        logger.info('Entering main loop...')
        while True:
            now = datetime.now()

            if now.hour == 3 and not trained_today:
                if data.get_days_count() >= 7:
                    all_data = data.get_all_historical_data()

                    model = train_model(transform_dataframe(all_data))
                trained_today = True
            elif now.hour != 3:
                trained_today = False

            time_window_df = extract_recent_window(cfg.namespace, deployment_name, service_name, minutes=20)
            if time_window_df.empty:
                logger.warning(f'Error getting data. Skipping Cycle.')
                time.sleep(60)
                continue

            raw_current_line = time_window_df.tail(1)
            data.append_metric(raw_current_line)

            transformed_df = transform_dataframe(time_window_df, is_training=False)

            if transformed_df.empty:
                logger.info('Waiting for cache to stabilize...')
                time.sleep(60)

            current_state = transformed_df.tail(1)

            total_cpu = current_state['cpu_usage'].values[0]
            total_mem = current_state['mem_usage'].values[0] / (1024 ** 3)
            current_replicas = current_state['replicas'].values[0]

            reative_replicas = calculate_reactive_hpa(total_cpu, total_mem, current_replicas, pod_cpu_req, pod_mem_req)
            days_history = data.get_days_count()

            if days_history < 7:
                final_replica_count = reative_replicas
                engine = "REACTIVE"
                logger.info(f'[WARMUP {days_history}/7d] Metrics: CPU={total_cpu:.2f} | Mem: {total_mem:.2f}GB | Current Replicas={current_replicas}')
            else:
                current_X = current_state[['cpu_usage', 'mem_usage', 'rps', 'hour', 'day_week', 'cpu_lag_15m', 'rps_lag_15m', 'cpu_per_request', 'mem_per_request']]

                try:
                    xgboost_predict = model.predict(current_X)
                    predicted_future_cpu = max(0.0, xgboost_predict[0][0])
                    predicted_future_mem_bytes = max(0.0, xgboost_predict[0][1])
                    predicted_future_mem_gb = predicted_future_mem_bytes / (1024 ** 3)
                    
                    xgboost_replicas = calculate_reactive_hpa(
                        cpu_usage_total=predicted_future_cpu, 
                        mem_usage_total=predicted_future_mem_gb,
                        current_replicas=current_replicas, 
                        pod_cpu_req=pod_cpu_req, 
                        pod_mem_req=pod_mem_req
                    )

                    final_replica_count = max(reative_replicas, xgboost_replicas)
                    engine = "PREDICTIVE (XGBoost)" if xgboost_replicas >= reative_replicas else "REACTIVE FALLBACK"
                    
                    logger.info(f'[PREDICTIVE]: Predicted CPU (+15m): {predicted_future_cpu:.2f} Cores | Predicted MEM (+15m): {predicted_future_mem_gb}Gb -> Replicas Needed: {xgboost_replicas} | Reactive calculated: {reative_replicas}')
                except NotFittedError:
                    pass
            logger.info(f"-> Shadow Mode Suggestion: Define replicas to {final_replica_count} (Engine: {engine})")

            time.sleep(60)


if __name__ == '__main__':
    logger.basicConfig(
        level=logger.INFO,
        format='[%(levelname)s] - %(asctime)s - %(message)s'
    )
    shadow_mode_controller()