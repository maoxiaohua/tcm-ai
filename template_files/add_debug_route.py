# 在main.py中添加调试路由
@app.get("/debug/doctor-login")
async def debug_doctor_login():
    """医生登录调试工具"""
    from fastapi.responses import FileResponse
    return FileResponse("/opt/tcm-ai/template_files/debug_doctor_login.html")