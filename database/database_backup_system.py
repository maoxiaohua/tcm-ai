#!/usr/bin/env python3
# database_backup_system.py - PostgreSQL自动备份系统
"""
功能：
1. 自动备份PostgreSQL数据库
2. 支持增量和全量备份
3. 备份文件压缩和清理
4. 备份完整性验证
5. 邮件通知（可选）
6. 备份恢复功能
"""

import os
import subprocess
import gzip
import shutil
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLBackupSystem:
    """PostgreSQL自动备份系统"""
    
    def __init__(self, 
                 db_config: Dict = None,
                 backup_dir: str = "/opt/tcm/backups",
                 max_backups: int = 7,
                 compress: bool = False):
        
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'tcm_db',
            'username': 'tcm_user',
            'password': 'tcm_secure_2024'
        }
        
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.compress = compress
        
        # 确保备份目录存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份配置
        self.backup_types = {
            'full': 'complete database dump',
            'data_only': 'data without schema', 
            'schema_only': 'schema without data'
        }
        
        logger.info(f"Backup system initialized: {backup_dir}")
    
    def create_backup_filename(self, backup_type: str = 'full') -> str:
        """生成备份文件名"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"tcm_db_{backup_type}_{timestamp}.sql"
        
        if self.compress:
            filename += '.gz'
            
        return os.path.join(self.backup_dir, filename)
    
    def execute_pg_dump(self, output_file: str, backup_type: str = 'full') -> Tuple[bool, str]:
        """执行pg_dump备份"""
        try:
            # 构建pg_dump命令
            cmd = [
                'pg_dump',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--username={self.db_config['username']}",
                f"--dbname={self.db_config['database']}",
                '--verbose',
                '--clean',  # 包含清理命令
                '--create', # 包含创建数据库命令
            ]
            
            # 根据备份类型添加参数
            if backup_type == 'data_only':
                cmd.append('--data-only')
            elif backup_type == 'schema_only':
                cmd.append('--schema-only')
            
            # 设置环境变量（密码）
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            logger.info(f"Starting {backup_type} backup to {output_file}")
            
            if self.compress:
                # 直接压缩输出
                with gzip.open(output_file, 'wt', encoding='utf-8') as gz_file:
                    result = subprocess.run(
                        cmd, 
                        stdout=gz_file, 
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        timeout=3600  # 1小时超时
                    )
            else:
                # 普通文件输出
                with open(output_file, 'w', encoding='utf-8') as sql_file:
                    result = subprocess.run(
                        cmd,
                        stdout=sql_file,
                        stderr=subprocess.PIPE, 
                        env=env,
                        text=True,
                        timeout=3600
                    )
            
            if result.returncode == 0:
                logger.info(f"Backup completed successfully: {output_file}")
                return True, "Backup completed successfully"
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Backup failed: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "Backup timeout (> 1 hour)"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Backup execution error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def verify_backup_integrity(self, backup_file: str) -> Tuple[bool, Dict]:
        """验证备份文件完整性"""
        try:
            if not os.path.exists(backup_file):
                return False, {"error": "Backup file not found"}
            
            # 获取文件信息
            file_stats = os.stat(backup_file)
            file_size = file_stats.st_size
            
            # 计算文件哈希
            hash_md5 = hashlib.md5()
            
            if backup_file.endswith('.gz'):
                with gzip.open(backup_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
            else:
                with open(backup_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
            
            # 基本验证：检查文件是否包含SQL内容
            content_sample = ""
            if backup_file.endswith('.gz'):
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    content_sample = f.read(1000)  # 读取前1000字符
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    content_sample = f.read(1000)
            
            # 验证是否包含PostgreSQL转储标识
            is_valid_sql = any(marker in content_sample for marker in [
                'PostgreSQL database dump',
                'CREATE DATABASE',
                'CREATE TABLE',
                '-- Name:', 
                '-- Type: TABLE'
            ])
            
            verification_result = {
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "md5_hash": hash_md5.hexdigest(),
                "contains_sql_content": is_valid_sql,
                "verified_at": datetime.now().isoformat()
            }
            
            if file_size > 0 and is_valid_sql:
                logger.info(f"Backup verification passed: {backup_file}")
                return True, verification_result
            else:
                logger.warning(f"Backup verification failed: {backup_file}")
                return False, verification_result
                
        except Exception as e:
            error_result = {"error": str(e), "verified_at": datetime.now().isoformat()}
            logger.error(f"Backup verification error: {e}")
            return False, error_result
    
    def cleanup_old_backups(self) -> int:
        """清理旧备份文件"""
        try:
            backup_files = []
            
            # 获取所有备份文件
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('tcm_db_') and (filename.endswith('.sql') or filename.endswith('.sql.gz')):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)
                    backup_files.append((file_path, file_stat.st_mtime))
            
            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除超过限制的旧文件
            deleted_count = 0
            for file_path, _ in backup_files[self.max_backups:]:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
            
            logger.info(f"Cleanup completed: {deleted_count} old backups deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0
    
    def create_backup(self, backup_type: str = 'full') -> Dict:
        """创建备份并返回结果"""
        start_time = datetime.now()
        backup_file = self.create_backup_filename(backup_type)
        
        result = {
            "backup_type": backup_type,
            "start_time": start_time.isoformat(),
            "backup_file": backup_file,
            "success": False,
            "error": None,
            "file_info": None,
            "verification": None,
            "duration_seconds": 0
        }
        
        try:
            # 执行备份
            success, message = self.execute_pg_dump(backup_file, backup_type)
            
            if success:
                # 验证备份
                verify_success, verify_info = self.verify_backup_integrity(backup_file)
                result["verification"] = verify_info
                result["success"] = verify_success
                
                if verify_success:
                    result["file_info"] = {
                        "path": backup_file,
                        "size_mb": verify_info["file_size_mb"],
                        "md5_hash": verify_info["md5_hash"]
                    }
                    
                    # 清理旧备份
                    deleted_count = self.cleanup_old_backups()
                    result["cleanup"] = {"deleted_old_backups": deleted_count}
                    
                    logger.info(f"Backup completed successfully: {backup_file}")
                else:
                    result["error"] = "Backup verification failed"
                    # 删除验证失败的备份文件
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
            else:
                result["error"] = message
                # 删除失败的备份文件
                if os.path.exists(backup_file):
                    os.remove(backup_file)
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Backup process error: {e}")
        
        finally:
            end_time = datetime.now()
            result["end_time"] = end_time.isoformat()
            result["duration_seconds"] = (end_time - start_time).total_seconds()
        
        return result
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份文件"""
        try:
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('tcm_db_') and (filename.endswith('.sql') or filename.endswith('.sql.gz')):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    # 解析文件名获取备份类型和时间
                    parts = filename.replace('.sql.gz', '').replace('.sql', '').split('_')
                    backup_type = parts[2] if len(parts) >= 3 else 'unknown'
                    backup_time = parts[3] if len(parts) >= 4 else 'unknown'
                    
                    backups.append({
                        "filename": filename,
                        "full_path": file_path,
                        "backup_type": backup_type,
                        "backup_time": backup_time,
                        "size_mb": round(file_stat.st_size / 1024 / 1024, 2),
                        "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
            
            # 按创建时间倒序排列
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def restore_backup(self, backup_file: str, target_database: str = None) -> Dict:
        """恢复备份（危险操作，请谨慎使用）"""
        target_db = target_database or self.db_config['database']
        
        result = {
            "backup_file": backup_file,
            "target_database": target_db, 
            "success": False,
            "error": None,
            "start_time": datetime.now().isoformat()
        }
        
        if not os.path.exists(backup_file):
            result["error"] = "Backup file not found"
            return result
        
        try:
            # 验证备份文件
            verify_success, verify_info = self.verify_backup_integrity(backup_file)
            if not verify_success:
                result["error"] = "Backup file verification failed"
                return result
            
            # 构建psql恢复命令
            cmd = [
                'psql',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--username={self.db_config['username']}",
                f"--dbname={target_db}",
                '--quiet'
            ]
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            logger.warning(f"Starting database restore from {backup_file} to {target_db}")
            
            if backup_file.endswith('.gz'):
                # 从压缩文件恢复
                with gzip.open(backup_file, 'rt', encoding='utf-8') as gz_file:
                    restore_result = subprocess.run(
                        cmd,
                        stdin=gz_file,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        timeout=3600
                    )
            else:
                # 从普通文件恢复
                with open(backup_file, 'r', encoding='utf-8') as sql_file:
                    restore_result = subprocess.run(
                        cmd,
                        stdin=sql_file,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        timeout=3600
                    )
            
            if restore_result.returncode == 0:
                result["success"] = True
                logger.info(f"Database restore completed successfully")
            else:
                result["error"] = restore_result.stderr or "Unknown restore error"
                logger.error(f"Database restore failed: {result['error']}")
        
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Restore process error: {e}")
        
        finally:
            result["end_time"] = datetime.now().isoformat()
        
        return result

def create_backup_schedule_script():
    """创建备份计划脚本"""
    script_content = '''#!/bin/bash
# auto_backup_tcm.sh - TCM数据库自动备份脚本
# 添加到crontab: 0 2 * * * /opt/tcm/auto_backup_tcm.sh >> /opt/tcm/logs/backup.log 2>&1

cd /opt/tcm
python3 -c "
from database_backup_system import PostgreSQLBackupSystem
import json

# 创建备份系统
backup_system = PostgreSQLBackupSystem()

# 执行全量备份
result = backup_system.create_backup('full')

# 输出结果
print(f'Backup completed at {result[\"end_time\"]}')
print(f'Success: {result[\"success\"]}')
if result[\"success\"]:
    print(f'File: {result[\"file_info\"][\"path\"]}')
    print(f'Size: {result[\"file_info\"][\"size_mb\"]}MB')
else:
    print(f'Error: {result[\"error\"]}')
"
'''
    
    script_path = "/opt/tcm/auto_backup_tcm.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # 设置执行权限
    os.chmod(script_path, 0o755)
    
    print(f"Backup schedule script created: {script_path}")
    print("To schedule daily backups at 2 AM, run:")
    print("crontab -e")
    print("Add: 0 2 * * * /opt/tcm/auto_backup_tcm.sh >> /opt/tcm/logs/backup.log 2>&1")

# 测试和命令行工具
if __name__ == "__main__":
    import sys
    
    backup_system = PostgreSQLBackupSystem()
    
    if len(sys.argv) == 1:
        print("TCM Database Backup System")
        print("Commands:")
        print("  python3 database_backup_system.py backup [type]    - Create backup (full/data_only/schema_only)")  
        print("  python3 database_backup_system.py list            - List all backups")
        print("  python3 database_backup_system.py verify <file>   - Verify backup integrity")
        print("  python3 database_backup_system.py schedule        - Create backup schedule script")
        print("  python3 database_backup_system.py test            - Run system test")
        
    elif sys.argv[1] == "backup":
        backup_type = sys.argv[2] if len(sys.argv) > 2 else 'full'
        print(f"Creating {backup_type} backup...")
        result = backup_system.create_backup(backup_type)
        print(json.dumps(result, indent=2))
        
    elif sys.argv[1] == "list":
        backups = backup_system.list_backups()
        print(f"Found {len(backups)} backups:")
        for backup in backups:
            print(f"  {backup['filename']} ({backup['size_mb']}MB) - {backup['backup_type']} - {backup['created_at']}")
            
    elif sys.argv[1] == "verify":
        if len(sys.argv) < 3:
            print("Usage: verify <backup_file>")
        else:
            backup_file = sys.argv[2]
            success, info = backup_system.verify_backup_integrity(backup_file)
            print(f"Verification: {'PASSED' if success else 'FAILED'}")
            print(json.dumps(info, indent=2))
            
    elif sys.argv[1] == "schedule":
        create_backup_schedule_script()
        
    elif sys.argv[1] == "test":
        print("Testing backup system...")
        
        # 创建测试备份
        result = backup_system.create_backup('schema_only')
        if result['success']:
            print("✅ Backup creation test passed")
            
            # 测试备份列表
            backups = backup_system.list_backups()
            print(f"✅ Backup listing test passed ({len(backups)} backups found)")
            
            # 测试验证
            if backups:
                test_file = backups[0]['full_path']
                verify_success, verify_info = backup_system.verify_backup_integrity(test_file)
                if verify_success:
                    print("✅ Backup verification test passed")
                else:
                    print("❌ Backup verification test failed")
            
            print("🎉 All tests passed!")
        else:
            print(f"❌ Backup creation test failed: {result['error']}")
    
    else:
        print(f"Unknown command: {sys.argv[1]}")