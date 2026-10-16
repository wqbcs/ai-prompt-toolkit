"""Dataset管理REST API — FastAPI路由

参考: langfuse Dataset API + promptfoo eval配置
- 数据集CRUD + 用例CRUD
- 导入/导出JSON/CSV
- 批量运行lint/scan/evaluate
- 评估矩阵(多模板×多维度的评分网格)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Query

if TYPE_CHECKING:
    from ai_prompt_toolkit.dataset import DatasetStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _get_store() -> DatasetStore:
    from ai_prompt_toolkit.dataset import DatasetStore

    return DatasetStore()


@router.get("")
async def api_list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    store = _get_store()
    datasets, total = store.list_datasets(page, page_size)
    return {
        "datasets": [d.to_dict() for d in datasets],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def api_create_dataset(body: dict[str, Any]) -> dict[str, Any]:
    store = _get_store()
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="缺少数据集名称")
    ds = store.create_dataset(name, description=body.get("description", ""), tags=body.get("tags", []))
    return {"status": "created", "dataset_id": ds.dataset_id}


@router.get("/{dataset_id}")
async def api_get_dataset(dataset_id: str) -> dict[str, Any]:
    store = _get_store()
    ds = store.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据集不存在")
    cases = store.get_cases(dataset_id)
    result = ds.to_dict()
    result["cases"] = [c.to_dict() for c in cases]
    return result


@router.delete("/{dataset_id}")
async def api_delete_dataset(dataset_id: str) -> dict[str, Any]:
    store = _get_store()
    if not store.delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    return {"status": "deleted"}


@router.post("/{dataset_id}/cases")
async def api_add_case(dataset_id: str, body: dict[str, Any]) -> dict[str, Any]:
    store = _get_store()
    if not store.get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    case = store.add_case(
        dataset_id,
        input_text=body.get("input", ""),
        expected_output=body.get("expected", ""),
        tags=body.get("tags", []),
        metadata=body.get("metadata", {}),
    )
    return {"status": "added", "case_id": case.case_id}


@router.delete("/{dataset_id}/cases/{case_id}")
async def api_delete_case(dataset_id: str, case_id: str) -> dict[str, Any]:
    store = _get_store()
    if not store.delete_case(case_id):
        raise HTTPException(status_code=404, detail="用例不存在")
    return {"status": "deleted"}


@router.post("/{dataset_id}/import")
async def api_import_dataset(dataset_id: str, body: dict[str, Any]) -> dict[str, Any]:
    store = _get_store()
    if not store.get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    fmt = body.get("format", "json")
    data = body.get("data", "")
    if fmt == "json":
        import json

        items = json.loads(data) if isinstance(data, str) else data
        count = store.import_json(dataset_id, items)
    elif fmt == "csv":
        count = store.import_csv(dataset_id, data)
    else:
        raise HTTPException(status_code=400, detail="不支持的格式，仅json/csv")
    return {"status": "imported", "count": count}


@router.get("/{dataset_id}/export")
async def api_export_dataset(dataset_id: str, fmt: str = Query("json")) -> dict[str, Any]:
    store = _get_store()
    if not store.get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    if fmt == "csv":
        return {"format": "csv", "data": store.export_csv(dataset_id)}
    return {"format": "json", "data": store.export_json(dataset_id)}


@router.post("/{dataset_id}/run")
async def api_run_dataset(dataset_id: str, body: dict[str, Any]) -> dict[str, Any]:
    store = _get_store()
    if not store.get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    run_type = body.get("run_type", "all")
    results = store.run_dataset(dataset_id, run_type=run_type)
    return {"status": "completed", "results": [r.to_dict() for r in results]}
