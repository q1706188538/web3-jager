# Web3钱包与自动代币接收工具

这个项目包含一个Web3钱包应用程序和一系列自动化工具，用于与BSC网络交互、接收代币和获取空投。

## 功能特点

1. **Web3钱包应用程序**
   - 创建和导入钱包
   - 查询BNB和代币余额
   - 转账BNB和代币
   - 与智能合约交互

2. **自动代币接收工具**
   - 监控代币余额变化
   - 自动接收代币交易
   - 自动处理空投
   - 监控区块链交易

## 文件说明

- `main.py` - Web3钱包应用程序主文件
- `app/wallet/wallet.py` - 钱包核心功能模块
- `airdrop_monitor.py` - 空投监控工具
- `auto_receiver.py` - 自动接收代币命令行工具
- `claim_jager_airdrop.py` - Jager代币空投领取工具
- `auto_token_receiver.py` - 自动代币接收和交易监控工具

## 安装

1. 确保已安装Python 3.8或更高版本
2. 安装依赖项：

```bash
pip install flask web3 python-dotenv
```

## 使用方法

### Web3钱包应用程序

启动Web3钱包应用程序：

```bash
python main.py
```

然后在浏览器中访问 http://localhost:5000

### 自动接收代币工具

#### 1. 监控空投

```bash
python airdrop_monitor.py
```

按照提示输入私钥和要监控的代币地址。

#### 2. 命令行工具

添加监控代币：

```bash
python auto_receiver.py add --token 0x代币地址 --private-key 您的私钥
```

开始监控：

```bash
python auto_receiver.py monitor --private-key 您的私钥 --interval 60
```

#### 3. Jager空投领取工具

```bash
python claim_jager_airdrop.py --private-key 您的私钥 --monitor
```

#### 4. 自动代币接收和交易监控

添加监控代币：

```bash
python auto_token_receiver.py add --token 0x代币地址 --private-key 您的私钥
```

开始监控交易：

```bash
python auto_token_receiver.py monitor --private-key 您的私钥 --interval 10
```

授权代币：

```bash
python auto_token_receiver.py approve --token 0x代币地址 --spender 0x被授权地址 --private-key 您的私钥
```

## 注意事项

1. **安全警告**：请勿在不安全的环境中输入您的私钥。
2. **测试网络**：建议先在测试网络上测试功能，添加 `--testnet` 参数使用BSC测试网。
3. **Gas费用**：所有写入操作（转账、授权等）都需要支付Gas费用，请确保您的钱包中有足够的BNB。

## 自定义配置

您可以修改 `.env` 文件来自定义配置：

```
# BSC网络配置
BSC_RPC_URL=https://bsc-dataseed.binance.org/
BSC_CHAIN_ID=56

# 测试网配置
BSC_TESTNET_RPC_URL=https://data-seed-prebsc-1-s1.binance.org:8545/
BSC_TESTNET_CHAIN_ID=97
```

## 示例：接收Jager代币空投

1. 导入您的钱包：

```bash
python auto_token_receiver.py import --private-key 您的私钥
```

2. 添加Jager代币到监控列表：

```bash
python auto_token_receiver.py add --token 0x74836cc0e821a6be18e407e6388e430b689c66e9 --private-key 您的私钥
```

3. 开始监控交易：

```bash
python auto_token_receiver.py monitor --private-key 您的私钥 --interval 10
```

4. 如果需要授权Jager代币：

```bash
python auto_token_receiver.py approve --token 0x74836cc0e821a6be18e407e6388e430b689c66e9 --spender 0x空投合约地址 --private-key 您的私钥
```

## 最新功能

### Web界面领取Jager空投

1. 启动Web应用程序：

```bash
python app.py
```

2. 在浏览器中访问 http://localhost:5000/jager

3. 输入私钥，设置Gas价格和Gas限制

4. 可选择启用自动转账功能，将领取到的Jager代币和BNB自动转移到指定地址

5. 点击"领取空投"按钮开始处理

### 转出全部BNB功能

1. 在Jager空投页面，将"保留BNB数量"设置为0，系统会自动从转账金额中扣除gas费用（含5%安全边际），尽可能转出钱包里的所有BNB

2. 在BNB转账页面，选中"转出全部BNB（自动扣除gas费）"选项，系统会自动计算gas费用并从总金额中扣除

### 批量处理多个钱包

1. 在Jager空投页面，启用"链式转账"功能

2. 输入多个私钥（每行一个）

3. 系统会在处理完一个钱包后，自动处理下一个钱包

## 贡献

欢迎提交问题和改进建议！
