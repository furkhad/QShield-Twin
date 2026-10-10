"""Pydantic schemas for devices and identity artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceBase(BaseModel):
    name: str
    model: Optional[str] = None
    pos_x: float = 0.0
    pos_y: float = 0.0


class DeviceCreate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    id: str
    is_active: bool
    created_at: datetime
    last_seen: datetime

    class Config:
        orm_mode = True


class IdentityClaimCreate(BaseModel):
    claimed_id: str
    signature: Optional[str] = None
    payload: Optional[str] = None


class IdentityClaimRead(IdentityClaimCreate):
    id: str
    device_id: str
    created_at: datetime

    class Config:
        orm_mode = True


class TrustRecordRead(BaseModel):
    id: str
    device_id: str
    score: float
    reason: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class LedgerEntryRead(BaseModel):
    id: str
    shard_id: int
    entry_type: str
    payload: str
    entry_hash: Optional[str]
    previous_hash: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
