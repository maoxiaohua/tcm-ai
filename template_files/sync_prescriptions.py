#!/usr/bin/env python3
"""
同步历史会话中的处方到处方表
"""
import sqlite3

conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
cursor = conn.cursor()

print('🔄 开始同步历史处方记录...')

# 获取有处方但没有创建处方记录的会话
cursor.execute("""
SELECT session_id, diagnosis_summary, prescription_given, created_at 
FROM conversation_metadata 
WHERE prescription_given <> '未开方' 
  AND session_id NOT IN (SELECT patient_id FROM prescriptions)
ORDER BY created_at DESC LIMIT 5
""")

sessions = cursor.fetchall()

if not sessions:
    print('✅ 没有需要同步的处方')
else:
    for session in sessions:
        session_id, diagnosis, prescription, created_at = session
        
        try:
            cursor.execute("""
                INSERT INTO prescriptions (
                    patient_id, conversation_id, symptoms, diagnosis, ai_prescription, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                f'conv_{session_id[:8]}',
                '患者咨询症状（历史记录同步）',
                diagnosis[:500] if diagnosis else '中医诊断分析',
                prescription,
                'pending',
                created_at
            ))
            
            prescription_id = cursor.lastrowid
            print(f'✅ 创建处方记录成功 - ID: {prescription_id}, Session: {session_id[:8]}...')
            
        except Exception as e:
            print(f'❌ 创建处方失败 {session_id[:8]}: {e}')

    conn.commit()

# 检查现在的处方总数
cursor.execute('SELECT COUNT(*) FROM prescriptions')
total_prescriptions = cursor.fetchone()[0]
print(f'📊 当前处方总数: {total_prescriptions}')

cursor.execute('SELECT COUNT(*) FROM prescriptions WHERE status = "pending"')
pending_prescriptions = cursor.fetchone()[0]
print(f'📋 待审查处方数: {pending_prescriptions}')

conn.close()
print('🎉 处方记录同步完成')