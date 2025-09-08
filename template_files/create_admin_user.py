#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建管理员用户用于测试
"""

import sqlite3
import hashlib
from datetime import datetime

def create_admin_user():
    """创建默认管理员用户"""
    db_path = "/opt/tcm-ai/data/user_history.sqlite"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建管理员账户表（独立于现有用户表）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_accounts (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 创建医生表（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license_no TEXT UNIQUE NOT NULL,
            phone TEXT,
            email TEXT,
            password_hash TEXT NOT NULL,
            speciality TEXT,
            hospital TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 创建默认管理员
    admin_password = "admin123"  # 临时密码，生产环境需要修改
    admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    now = datetime.now().isoformat()
    
    try:
        # 插入管理员用户
        cursor.execute("""
            INSERT OR REPLACE INTO admin_accounts 
            (user_id, username, email, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "admin_001", "admin", "admin@mxh0510.cn", admin_password_hash, 
            "admin", 1, now, now
        ))
        
        # 插入医生用户
        doctor_password_hash = hashlib.sha256("doctor123".encode()).hexdigest()
        cursor.execute("""
            INSERT OR REPLACE INTO admin_accounts 
            (user_id, username, email, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "doctor_001", "doctor", "doctor@mxh0510.cn", doctor_password_hash, 
            "doctor", 1, now, now
        ))
        
        # 插入到医生表
        cursor.execute("""
            INSERT OR REPLACE INTO doctors 
            (name, license_no, phone, email, password_hash, speciality, hospital, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "测试医生", "DOC001", "13800138000", "doctor@mxh0510.cn", 
            doctor_password_hash, "中医内科", "中医医院", "active", now, now
        ))
        
        # 插入患者用户
        patient_password_hash = hashlib.sha256("patient123".encode()).hexdigest()
        cursor.execute("""
            INSERT OR REPLACE INTO admin_accounts 
            (user_id, username, email, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "patient_001", "patient", "patient@mxh0510.cn", patient_password_hash, 
            "patient", 1, now, now
        ))
        
        conn.commit()
        print("✅ 默认用户创建成功！")
        print("管理员: admin / admin123")
        print("医生: doctor / doctor123") 
        print("患者: patient / patient123")
        
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_user()