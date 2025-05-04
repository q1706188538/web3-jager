# 部署指南

本文档提供了在服务器上部署 Jager 空投领取工具的步骤。

## 前提条件

- Python 3.8 或更高版本
- Git
- 具有公网 IP 的服务器（或使用内网穿透工具）

## 部署步骤

### 1. 克隆仓库

```bash
# 克隆仓库
git clone <远程仓库URL> jager-tool
cd jager-tool
```

### 2. 创建虚拟环境（可选但推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置应用程序

如果需要，可以创建 `.env` 文件来配置应用程序：

```
# BSC网络配置
BSC_RPC_URL=https://bsc-dataseed.binance.org/
BSC_CHAIN_ID=56

# 测试网配置
BSC_TESTNET_RPC_URL=https://data-seed-prebsc-1-s1.binance.org:8545/
BSC_TESTNET_CHAIN_ID=97
```

### 5. 运行应用程序

#### 开发环境

```bash
python app.py
```

#### 生产环境

对于生产环境，建议使用 Gunicorn（Linux/Mac）或 Waitress（Windows）作为 WSGI 服务器：

##### Linux/Mac（使用 Gunicorn）

```bash
# 安装 Gunicorn
pip install gunicorn

# 运行应用程序（使用flask_wsgi.py）
gunicorn -w 4 -b 0.0.0.0:8080 flask_wsgi:app
```

> 注意：如果遇到"无法找到'app'模块中的'app'属性"错误，请确保使用`flask_wsgi.py`文件。

##### Windows（使用 Waitress）

```bash
# 安装 Waitress
pip install waitress

# 创建 wsgi.py 文件
echo "from app import app\n\nif __name__ == '__main__':\n    from waitress import serve\n    serve(app, host='0.0.0.0', port=5000)" > wsgi.py

# 运行应用程序
python wsgi.py
```

### 6. 设置反向代理（可选但推荐）

对于生产环境，建议使用 Nginx 或 Apache 作为反向代理：

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Apache 配置示例

```apache
<VirtualHost *:80>
    ServerName your-domain.com

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/

    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

### 7. 设置自动启动（可选）

#### 使用 Systemd（Linux）

创建服务文件 `/etc/systemd/system/jager-tool.service`：

```ini
[Unit]
Description=Jager Airdrop Tool
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/jager-tool
ExecStart=/path/to/jager-tool/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable jager-tool
sudo systemctl start jager-tool
```

#### 使用 Windows 服务

对于 Windows，可以使用 NSSM（Non-Sucking Service Manager）将应用程序注册为服务：

1. 下载并安装 NSSM：https://nssm.cc/download
2. 打开命令提示符（以管理员身份运行）
3. 运行以下命令：

```batch
nssm install JagerTool
```

4. 在弹出的窗口中，设置以下参数：
   - Path: C:\path\to\jager-tool\venv\Scripts\python.exe
   - Startup directory: C:\path\to\jager-tool
   - Arguments: wsgi.py
5. 点击"Install service"按钮
6. 启动服务：

```batch
nssm start JagerTool
```

## 故障排除

### 1. 端口被占用

如果 5000 端口被占用，可以修改 `app.py` 文件中的端口号：

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

### 2. 网络连接问题

如果遇到网络连接问题，可能是 BSC 节点不稳定，可以尝试修改 `.env` 文件中的 RPC URL：

```
BSC_RPC_URL=https://bsc-dataseed1.defibit.io/
```

或者

```
BSC_RPC_URL=https://bsc-dataseed2.ninicoin.io/
```

### 3. 日志查看

如果使用 Systemd 部署，可以使用以下命令查看日志：

```bash
sudo journalctl -u jager-tool -f
```

如果使用 Windows 服务，可以在事件查看器中查看日志。
