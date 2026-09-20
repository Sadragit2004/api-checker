import logging

from celery import shared_task

from apps.price.services.source_sync import (
    sync_all_assets,
)


logger = logging.getLogger(__name__)


@shared_task(
    name="apps.price.tasks.sync_all_sources",
)
def sync_all_sources():

    logger.info(
        "Market source synchronization started."
    )

    results = sync_all_assets()

    success_count = sum(
        1
        for result in results
        if result.get("success")
    )

    failed_count = (
        len(results) - success_count
    )

    logger.info(
        "Market source synchronization finished | "
        "total=%s success=%s failed=%s",
        len(results),
        success_count,
        failed_count,
    )

    return {
        "total": len(results),
        "success": success_count,
        "failed": failed_count,
    }