from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging as logger
from config import Config

def discover_resources_by_labels() -> tuple[str, str]:
    cfg = Config()

    logger.debug('Trying to connect using kubeconfig...')
    try:
        config.load_kube_config()
        logger.debug('Logged in via kubeconfig.')
    except:
        logger.debug('Kubeconfig failed. Trying in-cluster...')
        try:
            config.load_incluster_config()
            logger.debug('Logged in via in-cluster config...')
        except:
            logger.exception('Error while connecting to the cluster.')

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    logger.info(f'Seaching for services with the labels {cfg.label_str}')
    try:
        services = core_v1.list_namespaced_service(namespace=cfg.namespace, label_selector=cfg.label_str)
    except ApiException:
        logger.exception('Error while listing services.')

    logger.info(f'Seaching for deployments with the labels {cfg.label_str}')
    try:
        deployments = apps_v1.list_namespaced_deployment(namespace=cfg.namespace, label_selector=cfg.label_str)
    except ApiException:
        logger.exception('Error while listing deployments.')

    return services.items[0].metadata.name, deployments.items[0].metadata.name
