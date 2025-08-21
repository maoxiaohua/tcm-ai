# TCM-AI 服务器配置文档

## 🌐 域名和SSL配置

### 当前域名
- **主域名**: `mxh0510.cn`
- **备用域名**: `www.mxh0510.cn`

### SSL证书位置
- **证书文件**: `/www/server/panel/vhost/cert/tcm-ai/fullchain.pem`
- **私钥文件**: `/www/server/panel/vhost/cert/tcm-ai/privkey.pem`
- **证书有效期**: 2025-06-30 到 2025-09-27

### Nginx配置
- **配置文件**: `/www/server/panel/vhost/nginx/tcm-ai.conf`
- **备份位置**: `/opt/tcm-ai/deploy/nginx_tcm_ai_backup.conf`

## 🚀 服务状态

### 主要服务
- **应用服务**: `tcm-ai.service` (端口8000)
- **Web服务器**: `nginx.service` (端口80/443)

### 服务检查命令
```bash
# 检查应用状态
systemctl status tcm-ai

# 检查nginx状态  
systemctl status nginx

# 检查端口监听
netstat -tuln | grep ":80\|:443\|:8000"

# 测试网站访问
curl -I https://mxh0510.cn
```

## 🛠️ 故障排除

### 常见问题

1. **HTTPS无法访问**
   - 检查nginx配置: `nginx -t`
   - 重载nginx: `systemctl reload nginx`
   - 检查证书有效期: `openssl x509 -in /www/server/panel/vhost/cert/tcm-ai/fullchain.pem -dates -noout`

2. **应用无响应**
   - 重启应用: `systemctl restart tcm-ai`
   - 查看日志: `journalctl -u tcm-ai -f`

3. **SSL证书过期**
   - 续期证书后更新路径: `/www/server/panel/vhost/cert/tcm-ai/`
   - 重载nginx配置

## 🔄 配置恢复

如果nginx配置丢失，使用备份恢复：
```bash
# 恢复nginx配置
cp /opt/tcm-ai/deploy/nginx_tcm_ai_backup.conf /www/server/panel/vhost/nginx/tcm-ai.conf

# 测试配置
nginx -t

# 重载nginx
systemctl reload nginx
```

## 📋 系统信息

- **系统名称**: tcm-ai (原ChineseMedicine)
- **项目路径**: `/opt/tcm-ai/`
- **静态文件**: `/opt/tcm-ai/static/`
- **应用端口**: 8000 (本地)
- **外部访问**: 443 (HTTPS), 80 (HTTP重定向)

---
*最后更新: 2025-08-20*