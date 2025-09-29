#!/usr/bin/env python3
"""
数据库一致性校验脚本
检查处方审核流程中的数据完整性和一致性
"""

import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append('/opt/tcm-ai')

class DatabaseConsistencyValidator:
    def __init__(self, db_path="/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.issues = []
        self.stats = {}
        
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def add_issue(self, category, description, severity="MEDIUM"):
        """添加问题到问题列表"""
        self.issues.append({
            "category": category,
            "description": description,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_db_connection(self):
        """获取数据库连接"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def check_table_exists(self):
        """检查必要的表是否存在"""
        self.log("检查数据库表结构...")
        
        required_tables = [
            'consultations',
            'prescriptions', 
            'doctor_review_queue',
            'prescription_review_history',
            'orders',
            'unified_users',
            'unified_sessions',
            'doctors'
        ]
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            existing_tables = [row['name'] for row in cursor.fetchall()]
            
            missing_tables = []
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
                    self.add_issue("TABLE_STRUCTURE", f"缺少必要的表: {table}", "HIGH")
            
            if missing_tables:
                self.log(f"❌ 缺少表: {', '.join(missing_tables)}")
            else:
                self.log("✅ 所有必要的表都存在")
            
            self.stats['total_tables'] = len(existing_tables)
            self.stats['missing_tables'] = len(missing_tables)
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查表结构时出错: {e}", "HIGH")
            self.log(f"❌ 检查表结构失败: {e}")
    
    def check_prescription_consistency(self):
        """检查处方数据一致性"""
        self.log("检查处方数据一致性...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查处方状态一致性
            cursor.execute("""
                SELECT COUNT(*) as count,
                       status,
                       review_status,
                       payment_status,
                       is_visible_to_patient
                FROM prescriptions 
                GROUP BY status, review_status, payment_status, is_visible_to_patient
            """)
            
            status_combinations = cursor.fetchall()
            self.log(f"发现 {len(status_combinations)} 种处方状态组合")
            
            # 2. 检查逻辑不一致的状态
            cursor.execute("""
                SELECT id, status, review_status, payment_status, is_visible_to_patient
                FROM prescriptions
                WHERE (
                    -- 审核通过但支付未完成却对患者可见
                    (review_status = 'approved' AND payment_status != 'completed' AND is_visible_to_patient = 1) OR
                    -- 未审核但对患者可见
                    (review_status IS NULL AND is_visible_to_patient = 1) OR
                    -- 审核拒绝但对患者可见
                    (review_status = 'rejected' AND is_visible_to_patient = 1)
                )
            """)
            
            inconsistent_prescriptions = cursor.fetchall()
            
            for prescription in inconsistent_prescriptions:
                self.add_issue(
                    "PRESCRIPTION_CONSISTENCY",
                    f"处方ID {prescription['id']} 状态不一致: "
                    f"status={prescription['status']}, "
                    f"review_status={prescription['review_status']}, "
                    f"payment_status={prescription['payment_status']}, "
                    f"visible={prescription['is_visible_to_patient']}",
                    "MEDIUM"
                )
            
            if inconsistent_prescriptions:
                self.log(f"❌ 发现 {len(inconsistent_prescriptions)} 个状态不一致的处方")
            else:
                self.log("✅ 处方状态一致性检查通过")
            
            # 3. 统计处方数据
            cursor.execute("SELECT COUNT(*) FROM prescriptions")
            self.stats['total_prescriptions'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE review_status = 'pending_review'")
            self.stats['pending_review'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE review_status = 'approved'")
            self.stats['approved'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE is_visible_to_patient = 1")
            self.stats['visible_to_patient'] = cursor.fetchone()[0]
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查处方一致性时出错: {e}", "HIGH")
            self.log(f"❌ 检查处方一致性失败: {e}")
    
    def check_review_queue_consistency(self):
        """检查审核队列一致性"""
        self.log("检查审核队列一致性...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查队列中的处方是否都存在
            cursor.execute("""
                SELECT drq.id, drq.prescription_id
                FROM doctor_review_queue drq
                LEFT JOIN prescriptions p ON drq.prescription_id = p.id
                WHERE p.id IS NULL
            """)
            
            orphaned_queue_records = cursor.fetchall()
            
            for record in orphaned_queue_records:
                self.add_issue(
                    "REVIEW_QUEUE_CONSISTENCY",
                    f"审核队列记录 {record['id']} 引用不存在的处方 {record['prescription_id']}",
                    "MEDIUM"
                )
            
            # 2. 检查已完成审核的处方是否还在待审核队列中
            cursor.execute("""
                SELECT drq.id, drq.prescription_id, p.review_status
                FROM doctor_review_queue drq
                JOIN prescriptions p ON drq.prescription_id = p.id
                WHERE drq.status = 'pending' AND p.review_status IN ('approved', 'rejected')
            """)
            
            stale_queue_records = cursor.fetchall()
            
            for record in stale_queue_records:
                self.add_issue(
                    "REVIEW_QUEUE_CONSISTENCY",
                    f"处方 {record['prescription_id']} 已审核({record['review_status']})但仍在待审核队列中",
                    "LOW"
                )
            
            # 3. 检查待审核处方是否都在队列中
            cursor.execute("""
                SELECT p.id
                FROM prescriptions p
                LEFT JOIN doctor_review_queue drq ON p.id = drq.prescription_id AND drq.status = 'pending'
                WHERE p.review_status = 'pending_review' AND drq.id IS NULL
            """)
            
            missing_queue_records = cursor.fetchall()
            
            for record in missing_queue_records:
                self.add_issue(
                    "REVIEW_QUEUE_CONSISTENCY",
                    f"处方 {record['id']} 状态为待审核但不在审核队列中",
                    "MEDIUM"
                )
            
            # 统计队列数据
            cursor.execute("SELECT COUNT(*) FROM doctor_review_queue WHERE status = 'pending'")
            self.stats['pending_reviews_in_queue'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM doctor_review_queue WHERE status = 'completed'")
            self.stats['completed_reviews_in_queue'] = cursor.fetchone()[0]
            
            total_issues = len(orphaned_queue_records) + len(stale_queue_records) + len(missing_queue_records)
            
            if total_issues == 0:
                self.log("✅ 审核队列一致性检查通过")
            else:
                self.log(f"❌ 发现 {total_issues} 个审核队列一致性问题")
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查审核队列一致性时出错: {e}", "HIGH")
            self.log(f"❌ 检查审核队列一致性失败: {e}")
    
    def check_payment_consistency(self):
        """检查支付数据一致性"""
        self.log("检查支付数据一致性...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查订单对应的处方是否存在
            cursor.execute("""
                SELECT o.id, o.order_no, o.prescription_id
                FROM orders o
                LEFT JOIN prescriptions p ON o.prescription_id = p.id
                WHERE p.id IS NULL
            """)
            
            orphaned_orders = cursor.fetchall()
            
            for order in orphaned_orders:
                self.add_issue(
                    "PAYMENT_CONSISTENCY",
                    f"订单 {order['order_no']} 引用不存在的处方 {order['prescription_id']}",
                    "MEDIUM"
                )
            
            # 2. 检查支付状态一致性
            cursor.execute("""
                SELECT o.order_no, o.payment_status as order_status, 
                       p.payment_status as prescription_status
                FROM orders o
                JOIN prescriptions p ON o.prescription_id = p.id
                WHERE o.payment_status != p.payment_status
            """)
            
            inconsistent_payments = cursor.fetchall()
            
            for payment in inconsistent_payments:
                self.add_issue(
                    "PAYMENT_CONSISTENCY",
                    f"订单 {payment['order_no']} 支付状态不一致: "
                    f"订单({payment['order_status']}) vs 处方({payment['prescription_status']})",
                    "MEDIUM"
                )
            
            # 3. 检查已支付但处方不可见的情况
            cursor.execute("""
                SELECT p.id, p.payment_status, p.review_status, p.is_visible_to_patient
                FROM prescriptions p
                WHERE p.payment_status = 'completed' 
                  AND p.review_status = 'approved' 
                  AND p.is_visible_to_patient = 0
            """)
            
            paid_but_invisible = cursor.fetchall()
            
            for prescription in paid_but_invisible:
                self.add_issue(
                    "PAYMENT_CONSISTENCY",
                    f"处方 {prescription['id']} 已支付且审核通过但对患者不可见",
                    "HIGH"
                )
            
            # 统计支付数据
            cursor.execute("SELECT COUNT(*) FROM orders")
            self.stats['total_orders'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'paid'")
            self.stats['paid_orders'] = cursor.fetchone()[0]
            
            total_issues = len(orphaned_orders) + len(inconsistent_payments) + len(paid_but_invisible)
            
            if total_issues == 0:
                self.log("✅ 支付数据一致性检查通过")
            else:
                self.log(f"❌ 发现 {total_issues} 个支付数据一致性问题")
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查支付数据一致性时出错: {e}", "HIGH")
            self.log(f"❌ 检查支付数据一致性失败: {e}")
    
    def check_consultation_consistency(self):
        """检查问诊记录一致性"""
        self.log("检查问诊记录一致性...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查处方对应的问诊记录是否存在
            cursor.execute("""
                SELECT p.id, p.consultation_id
                FROM prescriptions p
                LEFT JOIN consultations c ON p.consultation_id = c.uuid
                WHERE p.consultation_id IS NOT NULL AND c.uuid IS NULL
            """)
            
            orphaned_prescriptions = cursor.fetchall()
            
            for prescription in orphaned_prescriptions:
                self.add_issue(
                    "CONSULTATION_CONSISTENCY",
                    f"处方 {prescription['id']} 引用不存在的问诊记录 {prescription['consultation_id']}",
                    "MEDIUM"
                )
            
            # 2. 检查问诊记录的对话日志格式
            cursor.execute("""
                SELECT uuid, conversation_log
                FROM consultations
                WHERE conversation_log IS NOT NULL
            """)
            
            consultations = cursor.fetchall()
            invalid_logs = 0
            
            for consultation in consultations:
                try:
                    if consultation['conversation_log']:
                        log_data = json.loads(consultation['conversation_log'])
                        # 检查基本结构
                        if not isinstance(log_data, dict):
                            invalid_logs += 1
                            self.add_issue(
                                "CONSULTATION_CONSISTENCY",
                                f"问诊记录 {consultation['uuid']} 的conversation_log格式不正确",
                                "LOW"
                            )
                except json.JSONDecodeError:
                    invalid_logs += 1
                    self.add_issue(
                        "CONSULTATION_CONSISTENCY",
                        f"问诊记录 {consultation['uuid']} 的conversation_log不是有效的JSON",
                        "LOW"
                    )
            
            # 统计问诊数据
            cursor.execute("SELECT COUNT(*) FROM consultations")
            self.stats['total_consultations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM consultations WHERE status = 'completed'")
            self.stats['completed_consultations'] = cursor.fetchone()[0]
            
            total_issues = len(orphaned_prescriptions) + invalid_logs
            
            if total_issues == 0:
                self.log("✅ 问诊记录一致性检查通过")
            else:
                self.log(f"❌ 发现 {total_issues} 个问诊记录一致性问题")
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查问诊记录一致性时出错: {e}", "HIGH")
            self.log(f"❌ 检查问诊记录一致性失败: {e}")
    
    def check_user_data_consistency(self):
        """检查用户数据一致性"""
        self.log("检查用户数据一致性...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查处方患者ID是否有对应的用户记录（对于已注册用户）
            cursor.execute("""
                SELECT DISTINCT p.patient_id
                FROM prescriptions p
                LEFT JOIN unified_users uu ON p.patient_id = uu.global_user_id
                WHERE p.patient_id NOT LIKE 'guest%' 
                  AND p.patient_id NOT LIKE 'smart_user_%' 
                  AND uu.global_user_id IS NULL
            """)
            
            missing_users = cursor.fetchall()
            
            for user in missing_users:
                self.add_issue(
                    "USER_CONSISTENCY",
                    f"处方中的患者ID {user['patient_id']} 在用户表中不存在",
                    "LOW"
                )
            
            # 2. 检查问诊记录患者ID一致性
            cursor.execute("""
                SELECT DISTINCT c.patient_id
                FROM consultations c
                LEFT JOIN unified_users uu ON c.patient_id = uu.global_user_id
                WHERE c.patient_id NOT LIKE 'guest%' 
                  AND c.patient_id NOT LIKE 'smart_user_%'
                  AND uu.global_user_id IS NULL
            """)
            
            missing_consultation_users = cursor.fetchall()
            
            for user in missing_consultation_users:
                self.add_issue(
                    "USER_CONSISTENCY",
                    f"问诊记录中的患者ID {user['patient_id']} 在用户表中不存在",
                    "LOW"
                )
            
            # 统计用户数据
            cursor.execute("SELECT COUNT(*) FROM unified_users")
            self.stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM prescriptions")
            self.stats['unique_prescription_patients'] = cursor.fetchone()[0]
            
            total_issues = len(missing_users) + len(missing_consultation_users)
            
            if total_issues == 0:
                self.log("✅ 用户数据一致性检查通过")
            else:
                self.log(f"❌ 发现 {total_issues} 个用户数据一致性问题")
            
            conn.close()
            
        except Exception as e:
            self.add_issue("DATABASE", f"检查用户数据一致性时出错: {e}", "HIGH")
            self.log(f"❌ 检查用户数据一致性失败: {e}")
    
    def generate_report(self):
        """生成检查报告"""
        self.log("\n" + "="*60)
        self.log("数据库一致性检查报告")
        self.log("="*60)
        
        # 统计问题
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in self.issues if i['severity'] == 'MEDIUM']
        low_issues = [i for i in self.issues if i['severity'] == 'LOW']
        
        self.log(f"总问题数: {len(self.issues)}")
        self.log(f"  高严重性: {len(high_issues)}")
        self.log(f"  中严重性: {len(medium_issues)}")
        self.log(f"  低严重性: {len(low_issues)}")
        
        # 输出统计信息
        if self.stats:
            self.log("\n数据库统计:")
            for key, value in self.stats.items():
                self.log(f"  {key}: {value}")
        
        # 输出问题详情
        if self.issues:
            self.log("\n问题详情:")
            for issue in sorted(self.issues, key=lambda x: ['LOW', 'MEDIUM', 'HIGH'].index(x['severity']), reverse=True):
                severity_symbol = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[issue['severity']]
                self.log(f"{severity_symbol} [{issue['category']}] {issue['description']}")
        
        # 总体评估
        self.log("\n" + "="*60)
        if len(high_issues) == 0:
            if len(medium_issues) == 0:
                self.log("✅ 数据库一致性良好")
            else:
                self.log("⚠️ 数据库一致性基本良好，有少量中等问题")
        else:
            self.log("❌ 数据库存在严重的一致性问题，需要立即修复")
        
        return len(high_issues) == 0
    
    def run_all_checks(self):
        """运行所有一致性检查"""
        self.log("🔍 开始数据库一致性检查")
        
        checks = [
            ("表结构检查", self.check_table_exists),
            ("处方数据一致性", self.check_prescription_consistency),
            ("审核队列一致性", self.check_review_queue_consistency),
            ("支付数据一致性", self.check_payment_consistency),
            ("问诊记录一致性", self.check_consultation_consistency),
            ("用户数据一致性", self.check_user_data_consistency),
        ]
        
        for check_name, check_func in checks:
            self.log(f"\n{'='*50}")
            self.log(f"执行: {check_name}")
            try:
                check_func()
            except Exception as e:
                self.add_issue("SYSTEM", f"{check_name}执行失败: {e}", "HIGH")
                self.log(f"❌ {check_name}失败: {e}")
        
        # 生成报告
        return self.generate_report()

def main():
    """主函数"""
    print("数据库一致性校验脚本")
    print("=" * 50)
    
    validator = DatabaseConsistencyValidator()
    
    try:
        success = validator.run_all_checks()
        
        # 可选：将报告保存到文件
        if input("\n是否保存检查报告到文件？(y/N): ").lower() == 'y':
            report_file = f"/opt/tcm-ai/logs/db_consistency_report_{int(time.time())}.json"
            
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "total_issues": len(validator.issues),
                "statistics": validator.stats,
                "issues": validator.issues
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"报告已保存到: {report_file}")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ 检查过程中出现异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()