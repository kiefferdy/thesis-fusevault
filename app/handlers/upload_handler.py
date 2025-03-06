from fastapi import UploadFile, HTTPException
from typing import List, Dict, Any, Optional
from io import StringIO
import json
import pandas as pd
from app.services.asset_service import AssetService
import logging

logger = logging.getLogger(__name__)

class UploadHandler:
    def __init__(self):
        self.asset_service = AssetService()

    async def handle_json_files(
        self, files: List[UploadFile], wallet_address: str
    ) -> Dict[str, Any]:
        seen_asset_ids = set()
        results = []

        for file in files:
            if not file.filename.lower().endswith(".json"):
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": "Invalid file type; expected JSON."
                })
                continue

            try:
                content = await file.read()
                data = json.loads(content.decode("utf-8"))

                asset_id = data.get("asset_id")
                critical_metadata = data.get("critical_metadata")
                non_critical_metadata = data.get("non_critical_metadata", {})

                if not asset_id or not critical_metadata:
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "detail": "Missing required fields (asset_id, critical_metadata)."
                    })
                    continue

                if asset_id in seen_asset_ids:
                    results.append({
                        "asset_id": asset_id,
                        "filename": file.filename,
                        "status": "skipped",
                        "detail": "Duplicate asset_id in uploaded files."
                    })
                    continue

                seen_asset_ids.add(asset_id)

                asset_payload = {
                    "asset_id": asset_id,
                    "wallet_address": wallet_address,
                    "critical_metadata": critical_metadata,
                    "non_critical_metadata": non_critical_metadata
                }

                response = await self.asset_service.create_or_update_asset(asset_payload=asset_payload)

                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "detail": response
                })

            except json.JSONDecodeError:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": "Invalid JSON content."
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": f"Error processing file: {str(e)}"
                })

        return {
            "upload_count": len(results),
            "results": results
        }

    async def process_csv_upload(
        self,
        files: List[UploadFile],
        wallet_address: str,
        critical_metadata_fields: List[str]
    ) -> Dict[str, Any]:
        seen_asset_ids = set()
        results = []

        for file in files:
            if not file.filename.lower().endswith(".csv"):
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": "Invalid file type; expected CSV."
                })
                continue

            try:
                content = await file.read()
                csv_df = pd.read_csv(StringIO(content.decode("utf-8")))

                if "asset_id" not in csv_df.columns:
                    raise ValueError("CSV file must contain an 'asset_id' column.")

                missing_fields = [field for field in critical_metadata_fields if field not in csv_df.columns]
                if missing_fields:
                    raise ValueError(f"Missing critical columns: {missing_fields}")

                records = csv_df.to_dict(orient="records")

                results = []

                for record in records:
                    asset_id = str(record["asset_id"])
                    if asset_id in seen_asset_ids:
                        results.append({
                            "asset_id": asset_id,
                            "status": "skipped",
                            "detail": "Duplicate asset_id; skipping."
                        })
                        continue

                    seen_asset_ids.add(asset_id)

                    critical_md = {field: record[field] for field in critical_metadata_fields}
                    non_critical_md = {
                        k: v for k, v in record.items()
                        if k not in critical_metadata_fields and k != "asset_id"
                    }

                    asset_payload = {
                        "asset_id": asset_id,
                        "wallet_address": wallet_address,
                        "critical_metadata": critical_md,
                        "non_critical_metadata": non_critical_md
                    }

                    response = await self.asset_service.create_or_update_asset(asset_payload=asset_payload)

                    results.append({
                        "asset_id": asset_id,
                        "status": "success",
                        "detail": response
                    })

            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": f"Error processing CSV file: {str(e)}"
                })

        return {
            "upload_count": len(results),
            "results": results
        }
