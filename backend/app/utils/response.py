# app/utils/response.py
from typing import Any, Optional, Dict

def success(data: Optional[Any] = None, message: str = "OK", code: int = 200) -> Dict:
    return {
        "code": code,
        "success": True,
        "message": message,
        "data": data or {}
    }

def error(message: str = "Error", code: int = 400, err: Optional[Any] = None) -> Dict:
    return {
        "code": code,
        "success": False,
        "message": message,
        "error": err or {}
    }
