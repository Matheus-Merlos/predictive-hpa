import logging as logger
from datetime import datetime
from xgboost import XGBRegressor
import numpy as np
import time
import math

from database import DuckDBConnection
from prometheus_extract import extract_dataset, extract_recent_window
from feature_engineering import transform_dataframe
from predictor import train_model

DB_FILE = "/var/lib/predictive-hpa/duckdb.db"
REACTIVE_TARGET_CPU_UTILIZATION = 0.40
REACTIVE_TARGET_MEMORY_UTILIZATION_GB = 0.50
REACTIVE_TARGET_MAX_REPLICAS = 8
REACTIVE_TARGET_MIN_REPLICAS = 4

def calculate_reactive_hpa(cpu_usage_total, mem_usage_total, current_replicas):
    current_replicas_safe = max(current_replicas, 1)
    replicas_from_cpu = 0
    replicas_from_mem = 0

    if REACTIVE_TARGET_CPU_UTILIZATION is not None:
        cpu_per_pod = cpu_usage_total / current_replicas_safe
        replicas_from_cpu = math.ceil(current_replicas_safe * (cpu_per_pod / REACTIVE_TARGET_CPU_UTILIZATION))

    if REACTIVE_TARGET_MEMORY_UTILIZATION_GB is not None:
        mem_per_pod = mem_usage_total / current_replicas_safe
        replicas_from_mem = math.ceil(current_replicas_safe * (mem_per_pod / REACTIVE_TARGET_MEMORY_UTILIZATION_GB))

    desired_replicas = max(replicas_from_cpu, replicas_from_mem)

    desired_replicas = max(REACTIVE_TARGET_MIN_REPLICAS, desired_replicas)
    desired_replicas = min(REACTIVE_TARGET_MAX_REPLICAS, desired_replicas)

    return desired_replicas

def shadow_mode_controller():
    logger.info('Initializing Predictive-HPA Shadow Mode Controller...')
    with DuckDBConnection(DB_FILE) as data:
        logger.info('Gathering all available data on prometheus...')
        history_df = extract_dataset()

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

            model = train_model(transform_dataframe(all_data))
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

            time_window_df = extract_recent_window(minutes=20)
            if time_window_df.empty:
                logger.warning(f'Error getting data. Skipping Cycle.')
                time.sleep(60)
                continue

            raw_current_line = time_window_df.tail(1)
            data.append_metric(raw_current_line)

            transformed_df = transform_dataframe(time_window_df)

            if transformed_df.empty:
                logger.info('Waiting for cache to stabilize...')
                time.sleep(60)

            current_state = transformed_df.tail(1)

            total_cpu = current_state['cpu_usage'].values[0]
            total_mem = current_state['mem_usage'].values[0]
            current_replicas = current_state['replicas'].values[0]

            reative_replicas = calculate_reactive_hpa(total_cpu, total_mem, current_replicas)
            days_history = data.get_days_count()

            if days_history < 7:
                final_replica_count = reative_replicas
                engine = "REACTIVE"
                logger.info(f'[WARMUP {days_history}/7d] Metrics: CPU={total_cpu:.2f} | Current Replicas={current_replicas}')
            else:
                current_X = current_state[['cpu_usage', 'mem_usage', 'rps', 'hour', 'day_week', 'cpu_lag_15m', 'rps_lag_15m', 'cpu_per_request', 'mem_per_request']]
                xgboost_predict = model.predict(current_X)
                xgboost_replicas = int(np.ceil(xgboost_predict[0]))

                final_replica_count = max(reative_replicas, xgboost_replicas)
                engine = "PREDICTIVE (XGBoost)" if xgboost_replicas >= reative_replicas else "REACTIVE FALLBACK"

                logger.info(f'[PREDICTIVE]: XGBoost suggested: {xgboost_replicas} | Reactive calculated: {reative_replicas}')
            logger.info(f"-> Shadow Mode Suggestion: Define replicas to {final_replica_count} (Engine: {engine})")

            time.sleep(60)


if __name__ == '__main__':
    logger.basicConfig(
        level=logger.INFO,
        format='[%(levelname)s] - %(asctime)s - %(message)s'
    )
    shadow_mode_controller()