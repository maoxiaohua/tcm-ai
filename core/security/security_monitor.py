#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全监控和审计日志系统
实时监控系统安全状态，生成安全报告
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SecurityAlert:
    """安全告警"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    triggered_at: datetime
    user_id: Optional[str]
    ip_address: str
    event_count: int
    details: Dict[str, Any]
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class SystemMetrics:
    """系统安全指标"""
    timestamp: datetime
    total_sessions: int
    active_sessions: int
    failed_logins_1h: int
    suspicious_activities_1h: int
    api_calls_1h: int
    unique_ips_1h: int
    error_rate_1h: float
    avg_response_time_ms: float

class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.active_alerts: Dict[str, SecurityAlert] = {}
        self._init_monitoring_tables()
        
        # 告警规则配置
        self.alert_rules = {
            "failed_login_threshold": 5,        # 1小时内失败登录次数
            "suspicious_ip_threshold": 10,      # 单个IP异常活动次数
            "api_rate_limit": 1000,            # 每小时API调用限制
            "session_timeout_minutes": 30,     # 会话超时时间
            "error_rate_threshold": 0.1        # 错误率阈值 10%
        }
    
    def _init_monitoring_tables(self):
        """初始化监控数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 安全告警表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                alert_id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                triggered_at TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                event_count INTEGER DEFAULT 1,
                details TEXT,
                is_resolved INTEGER DEFAULT 0,
                resolved_at TEXT
            )
        """)
        
        # 系统指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_sessions INTEGER,
                active_sessions INTEGER,
                failed_logins_1h INTEGER,
                suspicious_activities_1h INTEGER,
                api_calls_1h INTEGER,
                unique_ips_1h INTEGER,
                error_rate_1h REAL,
                avg_response_time_ms REAL
            )
        """)
        
        # API访问日志表（用于监控）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                method TEXT,
                endpoint TEXT,
                status_code INTEGER,
                response_time_ms REAL,
                user_id TEXT,
                session_token TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def analyze_security_events(self) -> List[SecurityAlert]:
        """分析安全事件，生成告警"""
        alerts = []
        
        # 分析失败登录
        alerts.extend(self._analyze_failed_logins())
        
        # 分析可疑IP活动
        alerts.extend(self._analyze_suspicious_ips())
        
        # 分析API访问异常
        alerts.extend(self._analyze_api_anomalies())
        
        # 分析会话异常
        alerts.extend(self._analyze_session_anomalies())
        
        # 保存告警到数据库
        for alert in alerts:
            self._save_alert(alert)
            self.active_alerts[alert.alert_id] = alert
        
        return alerts
    
    def _analyze_failed_logins(self) -> List[SecurityAlert]:
        """分析失败登录尝试"""
        alerts = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询1小时内的失败登录
        since = (datetime.now() - timedelta(hours=1)).isoformat()
        
        cursor.execute("""
            SELECT ip_address, COUNT(*) as fail_count
            FROM security_events
            WHERE event_type = 'LOGIN_FAILED' AND timestamp > ?
            GROUP BY ip_address
            HAVING COUNT(*) >= ?
        """, (since, self.alert_rules["failed_login_threshold"]))
        
        for row in cursor.fetchall():
            ip_address, fail_count = row
            
            alert = SecurityAlert(
                alert_id=f"failed_login_{ip_address}_{datetime.now().strftime('%Y%m%d%H')}",
                level=AlertLevel.WARNING,
                title=f"可疑登录尝试",
                description=f"IP {ip_address} 在1小时内失败登录 {fail_count} 次",
                triggered_at=datetime.now(),
                user_id=None,
                ip_address=ip_address,
                event_count=fail_count,
                details={"threshold": self.alert_rules["failed_login_threshold"]}
            )
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    def _analyze_suspicious_ips(self) -> List[SecurityAlert]:
        """分析可疑IP活动"""
        alerts = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # 查询异常活跃的IP
        cursor.execute("""
            SELECT ip_address, COUNT(*) as event_count,
                   COUNT(DISTINCT event_type) as event_types,
                   GROUP_CONCAT(DISTINCT event_type) as events
            FROM security_events
            WHERE timestamp > ? AND risk_level IN ('HIGH', 'CRITICAL')
            GROUP BY ip_address
            HAVING COUNT(*) >= ?
        """, (since, self.alert_rules["suspicious_ip_threshold"]))
        
        for row in cursor.fetchall():
            ip_address, event_count, event_types, events = row
            
            alert = SecurityAlert(
                alert_id=f"suspicious_ip_{ip_address}_{datetime.now().strftime('%Y%m%d%H')}",
                level=AlertLevel.CRITICAL,
                title=f"可疑IP活动",
                description=f"IP {ip_address} 产生 {event_count} 个高风险事件",
                triggered_at=datetime.now(),
                user_id=None,
                ip_address=ip_address,
                event_count=event_count,
                details={
                    "event_types": event_types,
                    "events": events.split(',') if events else []
                }
            )
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    def _analyze_api_anomalies(self) -> List[SecurityAlert]:
        """分析API访问异常"""
        alerts = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # 查询API调用频率异常
        cursor.execute("""
            SELECT ip_address, COUNT(*) as api_calls,
                   COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_calls
            FROM api_access_log
            WHERE timestamp > ?
            GROUP BY ip_address
            HAVING COUNT(*) >= ?
        """, (since, self.alert_rules["api_rate_limit"]))
        
        for row in cursor.fetchall():
            ip_address, api_calls, error_calls = row
            error_rate = error_calls / api_calls if api_calls > 0 else 0
            
            # 高频率访问告警
            if api_calls >= self.alert_rules["api_rate_limit"]:
                alert = SecurityAlert(
                    alert_id=f"api_rate_{ip_address}_{datetime.now().strftime('%Y%m%d%H')}",
                    level=AlertLevel.WARNING,
                    title=f"API访问频率异常",
                    description=f"IP {ip_address} 在1小时内调用API {api_calls} 次",
                    triggered_at=datetime.now(),
                    user_id=None,
                    ip_address=ip_address,
                    event_count=api_calls,
                    details={
                        "error_rate": error_rate,
                        "error_calls": error_calls
                    }
                )
                alerts.append(alert)
            
            # 高错误率告警
            if error_rate >= self.alert_rules["error_rate_threshold"]:
                alert = SecurityAlert(
                    alert_id=f"api_errors_{ip_address}_{datetime.now().strftime('%Y%m%d%H')}",
                    level=AlertLevel.CRITICAL,
                    title=f"API错误率异常",
                    description=f"IP {ip_address} API错误率 {error_rate:.1%}",
                    triggered_at=datetime.now(),
                    user_id=None,
                    ip_address=ip_address,
                    event_count=error_calls,
                    details={
                        "total_calls": api_calls,
                        "error_rate": error_rate
                    }
                )
                alerts.append(alert)
        
        conn.close()
        return alerts
    
    def _analyze_session_anomalies(self) -> List[SecurityAlert]:
        """分析会话异常"""
        alerts = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询长时间无活动的会话
        inactive_threshold = (datetime.now() - timedelta(minutes=self.alert_rules["session_timeout_minutes"])).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) as inactive_sessions
            FROM user_sessions
            WHERE is_active = 1 AND last_activity < ?
        """, (inactive_threshold,))
        
        inactive_count = cursor.fetchone()[0]
        
        if inactive_count > 0:
            alert = SecurityAlert(
                alert_id=f"inactive_sessions_{datetime.now().strftime('%Y%m%d%H%M')}",
                level=AlertLevel.INFO,
                title=f"检测到非活跃会话",
                description=f"{inactive_count} 个会话超过 {self.alert_rules['session_timeout_minutes']} 分钟无活动",
                triggered_at=datetime.now(),
                user_id=None,
                ip_address="system",
                event_count=inactive_count,
                details={"timeout_minutes": self.alert_rules["session_timeout_minutes"]}
            )
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    def get_system_metrics(self) -> SystemMetrics:
        """获取系统安全指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        hour_ago = (now - timedelta(hours=1)).isoformat()
        
        # 获取会话统计
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
        active_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        total_sessions = cursor.fetchone()[0]
        
        # 获取1小时内的安全事件统计
        cursor.execute("""
            SELECT COUNT(*) FROM security_events 
            WHERE event_type = 'LOGIN_FAILED' AND timestamp > ?
        """, (hour_ago,))
        failed_logins = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM security_events 
            WHERE risk_level IN ('HIGH', 'CRITICAL') AND timestamp > ?
        """, (hour_ago,))
        suspicious_activities = cursor.fetchone()[0]
        
        # 获取API统计
        cursor.execute("""
            SELECT COUNT(*), COUNT(DISTINCT ip_address),
                   AVG(CASE WHEN status_code >= 400 THEN 1.0 ELSE 0.0 END) as error_rate,
                   AVG(response_time_ms)
            FROM api_access_log WHERE timestamp > ?
        """, (hour_ago,))
        
        api_row = cursor.fetchone()
        api_calls = api_row[0] if api_row else 0
        unique_ips = api_row[1] if api_row else 0
        error_rate = api_row[2] if api_row and api_row[2] else 0.0
        avg_response_time = api_row[3] if api_row and api_row[3] else 0.0
        
        conn.close()
        
        metrics = SystemMetrics(
            timestamp=now,
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            failed_logins_1h=failed_logins,
            suspicious_activities_1h=suspicious_activities,
            api_calls_1h=api_calls,
            unique_ips_1h=unique_ips,
            error_rate_1h=error_rate,
            avg_response_time_ms=avg_response_time
        )
        
        # 保存指标到数据库
        self._save_metrics(metrics)
        
        return metrics
    
    def _save_alert(self, alert: SecurityAlert):
        """保存告警到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO security_alerts
            (alert_id, level, title, description, triggered_at, user_id, ip_address,
             event_count, details, is_resolved, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id, alert.level.value, alert.title, alert.description,
            alert.triggered_at.isoformat(), alert.user_id, alert.ip_address,
            alert.event_count, json.dumps(alert.details), 
            int(alert.is_resolved), 
            alert.resolved_at.isoformat() if alert.resolved_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _save_metrics(self, metrics: SystemMetrics):
        """保存系统指标到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_metrics
            (timestamp, total_sessions, active_sessions, failed_logins_1h,
             suspicious_activities_1h, api_calls_1h, unique_ips_1h,
             error_rate_1h, avg_response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp.isoformat(), metrics.total_sessions,
            metrics.active_sessions, metrics.failed_logins_1h,
            metrics.suspicious_activities_1h, metrics.api_calls_1h,
            metrics.unique_ips_1h, metrics.error_rate_1h,
            metrics.avg_response_time_ms
        ))
        
        conn.commit()
        conn.close()
    
    def log_api_access(self, ip_address: str, user_agent: str, method: str,
                      endpoint: str, status_code: int, response_time_ms: float,
                      user_id: Optional[str] = None, session_token: Optional[str] = None):
        """记录API访问日志"""
        try:
            # 🔑 修复：添加超时和错误处理，避免数据库锁定影响API性能
            conn = sqlite3.connect(self.db_path, timeout=1.0)  # 1秒超时
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO api_access_log
                (timestamp, ip_address, user_agent, method, endpoint, status_code,
                 response_time_ms, user_id, session_token)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), ip_address, user_agent, method,
                endpoint, status_code, response_time_ms, user_id, session_token
            ))
            
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            # 数据库锁定时静默失败，不影响API正常运行
            print(f"⚠️ API访问日志记录失败: {e}")
        except Exception as e:
            # 其他错误也不影响API
            print(f"⚠️ 安全监控记录失败: {e}")
    
    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """获取安全仪表板数据"""
        metrics = self.get_system_metrics()
        alerts = list(self.active_alerts.values())
        
        # 按级别统计告警
        alert_stats = defaultdict(int)
        for alert in alerts:
            if not alert.is_resolved:
                alert_stats[alert.level.value] += 1
        
        # 获取最近24小时的趋势数据
        trend_data = self._get_trend_data()
        
        return {
            "current_metrics": asdict(metrics),
            "active_alerts": [asdict(alert) for alert in alerts if not alert.is_resolved],
            "alert_statistics": dict(alert_stats),
            "trend_data": trend_data,
            "system_status": self._calculate_system_status(metrics, alerts)
        }
    
    def _get_trend_data(self) -> Dict[str, List]:
        """获取趋势数据（最近24小时）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, failed_logins_1h, suspicious_activities_1h,
                   api_calls_1h, error_rate_1h
            FROM system_metrics
            WHERE timestamp > ?
            ORDER BY timestamp
        """, (since,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {}
        
        timestamps = []
        failed_logins = []
        suspicious_activities = []
        api_calls = []
        error_rates = []
        
        for row in rows:
            timestamps.append(row[0])
            failed_logins.append(row[1])
            suspicious_activities.append(row[2])
            api_calls.append(row[3])
            error_rates.append(row[4])
        
        return {
            "timestamps": timestamps,
            "failed_logins": failed_logins,
            "suspicious_activities": suspicious_activities,
            "api_calls": api_calls,
            "error_rates": error_rates
        }
    
    def _calculate_system_status(self, metrics: SystemMetrics, 
                               alerts: List[SecurityAlert]) -> str:
        """计算系统整体安全状态"""
        critical_alerts = sum(1 for a in alerts if not a.is_resolved and a.level == AlertLevel.CRITICAL)
        warning_alerts = sum(1 for a in alerts if not a.is_resolved and a.level == AlertLevel.WARNING)
        
        if critical_alerts > 0:
            return "CRITICAL"
        elif warning_alerts > 3:
            return "WARNING"
        elif metrics.error_rate_1h > self.alert_rules["error_rate_threshold"]:
            return "WARNING"
        else:
            return "HEALTHY"

# 全局实例
security_monitor = SecurityMonitor()