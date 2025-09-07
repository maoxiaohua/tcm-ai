"""
医生客户端闭环系统 - 数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class PrescriptionStatus(Enum):
    """处方状态枚举"""
    PENDING = "pending"
    DOCTOR_REVIEWING = "doctor_reviewing" 
    APPROVED = "approved"
    REJECTED = "rejected"
    PATIENT_CONFIRMED = "patient_confirmed"
    PAID = "paid"
    DECOCTION_SUBMITTED = "decoction_submitted"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"

class PaymentStatus(Enum):
    """支付状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class DoctorStatus(Enum):
    """医生状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

@dataclass
class Doctor:
    """医生模型"""
    id: Optional[int] = None
    name: str = ""
    license_no: str = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    speciality: Optional[str] = None
    hospital: Optional[str] = None
    auth_token: Optional[str] = None
    password_hash: Optional[str] = None
    status: str = DoctorStatus.ACTIVE.value
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

@dataclass
class Prescription:
    """处方模型"""
    id: Optional[int] = None
    patient_id: str = ""
    conversation_id: str = ""
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    ai_prescription: str = ""
    doctor_prescription: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_notes: Optional[str] = None
    status: str = PrescriptionStatus.PENDING.value
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    version: int = 1

@dataclass
class Order:
    """订单模型"""
    id: Optional[int] = None
    order_no: str = ""
    prescription_id: int = 0
    patient_id: str = ""
    amount: float = 0.0
    payment_method: Optional[str] = None
    payment_status: str = PaymentStatus.PENDING.value
    payment_time: Optional[datetime] = None
    payment_transaction_id: Optional[str] = None
    decoction_required: bool = False
    shipping_name: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DecoctionOrder:
    """代煎订单模型"""
    id: Optional[int] = None
    order_id: int = 0
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    decoction_order_no: Optional[str] = None
    status: str = "submitted"
    tracking_no: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    provider_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class PrescriptionChange:
    """处方变更记录模型"""
    id: Optional[int] = None
    prescription_id: int = 0
    changed_by: int = 0
    change_type: str = ""
    original_prescription: Optional[str] = None
    new_prescription: Optional[str] = None
    change_reason: Optional[str] = None
    created_at: Optional[datetime] = None