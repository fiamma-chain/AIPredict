# 🔐 安全最佳实践指南

## ⚠️ 安全风险评估

### .env 文件存储私钥和API的风险

#### 当前风险等级：🟡 中等

**风险点：**
- ❌ 纯文本存储私钥
- ❌ 如果被误提交到Git会泄露
- ❌ 如果服务器被入侵可直接读取
- ❌ 系统管理员可以访问

**已有防护：**
- ✅ .env 在 .gitignore 中（不会提交到Git）
- ✅ 仅本地文件系统访问
- ✅ 需要文件系统权限才能读取

---

## 🛡️ 当前系统的安全措施

### 1. Git 保护

```bash
# .gitignore 已包含
.env
*.env
.env.*
```

**效果：** 防止私钥被提交到代码仓库

### 2. 文件权限

建议设置：
```bash
chmod 600 .env
```

**效果：** 只有文件所有者可以读写

### 3. 不同环境隔离

```bash
.env.local    # 本地开发
.env.prod     # 生产环境
.env.test     # 测试环境
```

---

## 🔒 更安全的方案

### 方案 A：系统密钥管理器（推荐）⭐⭐⭐⭐⭐

#### macOS Keychain

**优势：**
- 加密存储
- 系统级保护
- 需要密码访问

**实现：**

```bash
# 存储私钥到 Keychain
security add-generic-password \
  -a "$USER" \
  -s "hyperliquid_private_key" \
  -w "0x你的私钥"

# 存储 API Key
security add-generic-password \
  -a "$USER" \
  -s "claude_api_key" \
  -w "sk-ant-xxx..."
```

**在代码中读取：**
```python
import subprocess

def get_keychain_password(service_name):
    try:
        result = subprocess.run([
            'security', 'find-generic-password',
            '-a', os.getenv('USER'),
            '-s', service_name,
            '-w'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return None

# 使用
private_key = get_keychain_password('hyperliquid_private_key')
claude_key = get_keychain_password('claude_api_key')
```

---

### 方案 B：加密 .env 文件 ⭐⭐⭐⭐

#### 使用 age 或 sops 加密

**工具：**
```bash
# 安装 age（推荐）
brew install age

# 生成密钥对
age-keygen -o key.txt

# 加密 .env
age -r $(cat key.txt | grep public) -o .env.enc .env

# 删除原始 .env
shred -u .env  # Linux
rm -P .env     # macOS

# 使用时解密
age -d -i key.txt .env.enc > .env
```

**流程：**
1. 将 .env 加密为 .env.enc
2. 只提交 .env.enc 到 Git
3. key.txt 存在安全位置（不提交）
4. 启动前自动解密

---

### 方案 C：环境变量注入 ⭐⭐⭐

**不使用 .env 文件，直接用环境变量：**

```bash
# 在 ~/.zshrc 或 ~/.bashrc 中
export HYPERLIQUID_PRIVATE_KEY="0x..."
export CLAUDE_API_KEY="sk-ant-..."

# 或在启动时注入
HYPERLIQUID_PRIVATE_KEY="0x..." \
CLAUDE_API_KEY="sk-ant-..." \
python3 arena_main.py
```

**优势：**
- 不存储在文件中
- 每次会话独立

**劣势：**
- 配置麻烦
- 在进程列表中可见

---

### 方案 D：硬件钱包 ⭐⭐⭐⭐⭐

**最安全方案（仅适用于私钥）：**

- 使用 Ledger/Trezor 等硬件钱包
- 私钥永不离开设备
- 每次交易需要物理确认

**限制：**
- Hyperliquid 需要支持硬件钱包
- 自动交易不适用（需要人工确认）

---

### 方案 E：云密钥管理服务 ⭐⭐⭐⭐

**专业方案：**

#### AWS Secrets Manager
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']
```

#### HashiCorp Vault
```python
import hvac

client = hvac.Client(url='http://localhost:8200')
secret = client.secrets.kv.v2.read_secret_version(
    path='aitrading/keys'
)
```

**优势：**
- 企业级加密
- 访问审计
- 权限控制

**劣势：**
- 需要额外服务
- 配置复杂

---

## 💡 推荐方案对比

| 方案 | 安全性 | 易用性 | 成本 | 适合场景 |
|------|--------|--------|------|----------|
| .env 文件 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 | 个人测试 |
| Keychain | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | 个人使用 |
| 加密文件 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | 团队开发 |
| 环境变量 | ⭐⭐⭐ | ⭐⭐ | 免费 | 临时使用 |
| 硬件钱包 | ⭐⭐⭐⭐⭐ | ⭐ | $50-150 | 大额资金 |
| 云密钥管理 | ⭐⭐⭐⭐⭐ | ⭐⭐ | $$ | 生产环境 |

---

## 🎯 针对你的使用场景

### 场景 1：个人测试（小额资金）

**推荐：** .env + 基础防护

```bash
# 1. 确保 .gitignore 包含 .env
echo ".env" >> .gitignore

# 2. 设置文件权限
chmod 600 .env

# 3. 定期检查
git status | grep .env  # 不应出现
```

**风险可接受：**
- 测试网无风险
- 主网小额（100-500U）可接受

---

### 场景 2：个人正式使用（中等资金）

**推荐：** macOS Keychain

我可以帮你实现自动从 Keychain 读取：

```python
# config/secure_settings.py
import os
import subprocess
from pydantic_settings import BaseSettings

class SecureSettings(BaseSettings):
    def _get_keychain(self, service_name: str) -> str:
        try:
            result = subprocess.run([
                'security', 'find-generic-password',
                '-a', os.getenv('USER'),
                '-s', service_name,
                '-w'
            ], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return ""
    
    @property
    def hyperliquid_private_key(self):
        return self._get_keychain('hyperliquid_private_key')
    
    @property
    def claude_api_key(self):
        return self._get_keychain('claude_api_key')
```

**设置步骤：**
```bash
# 一次性设置
./setup_keychain.sh
```

---

### 场景 3：团队开发

**推荐：** 加密 .env 文件

```bash
# 1. 加密
age -r $(cat team-key.pub) -o .env.enc .env

# 2. 提交加密文件
git add .env.enc
git commit -m "Add encrypted config"

# 3. 团队成员解密
age -d -i team-key.txt .env.enc > .env
```

---

### 场景 4：生产环境（大额资金）

**推荐：** 云密钥管理 + 硬件钱包

- API Keys → AWS Secrets Manager
- 私钥 → 硬件钱包（手动确认重要交易）

---

## 🚨 安全检查清单

### 日常检查

- [ ] .env 不在 Git 中
- [ ] .env 文件权限 600
- [ ] 没有在日志中打印私钥
- [ ] 没有截图包含私钥
- [ ] 不通过网络传输私钥

### 代码检查

```bash
# 1. 检查是否误提交
git log --all --full-history --source --pretty=fuller -S "sk-ant-"

# 2. 检查当前分支
git diff HEAD | grep -i "private\|secret\|key"

# 3. 扫描敏感信息
grep -r "0x[a-fA-F0-9]{64}" . --exclude-dir=.git
```

### 服务器检查

- [ ] SSH 密钥登录（禁用密码）
- [ ] 防火墙配置正确
- [ ] 定期更新系统
- [ ] 最小权限原则
- [ ] 监控异常访问

---

## 🛠️ 立即改进

### 快速安全加固（5分钟）

```bash
# 1. 设置 .env 权限
chmod 600 .env

# 2. 确保不会提交
git update-index --assume-unchanged .env

# 3. 添加提交前检查
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
if git diff --cached --name-only | grep -q "\.env$"; then
    echo "错误: 不能提交 .env 文件！"
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit

# 4. 创建 .env 模板
cp .env .env.example
# 手动删除 .env.example 中的真实密钥
git add .env.example
```

### 升级到 Keychain（15分钟）

我可以为你创建一个自动化脚本：

```bash
./scripts/migrate_to_keychain.sh
```

这个脚本会：
1. 读取当前 .env
2. 存储到 Keychain
3. 加密备份 .env
4. 清除原始 .env
5. 修改代码使用 Keychain

---

## 📊 安全建议总结

### 个人使用（你的情况）

**当前方案（可接受）：**
- .env 文件 + 权限控制
- 测试网无风险
- 主网小额可接受

**建议升级（如果资金 > 1000U）：**
1. 使用 macOS Keychain
2. 或加密 .env 文件
3. 定期检查安全性

**必做的事：**
```bash
# 1. 立即执行
chmod 600 .env
git update-index --assume-unchanged .env

# 2. 验证
ls -la .env  # 应该是 -rw------- (600)
git status   # 不应该显示 .env
```

---

## 🆘 如果私钥泄露

### 立即行动：

1. **停止所有程序**
   ```bash
   pkill -f arena_main
   ```

2. **转移资金**
   - 立即将资金转到新地址
   - 使用 Hyperliquid 界面手动操作

3. **撤销 API Keys**
   - Claude: console.anthropic.com
   - OpenAI: platform.openai.com
   - 其他：对应平台

4. **生成新密钥**
   ```bash
   python3 generate_account.py
   ```

5. **更新所有配置**

---

## 💡 你现在应该做什么？

### 选项 A：保持现状 + 基础加固（推荐）

```bash
# 2分钟搞定
chmod 600 .env
git update-index --assume-unchanged .env
echo "✅ 基础安全已加固"
```

**适合：** 测试阶段，小额资金（< 500U）

### 选项 B：升级到 Keychain（需要我帮你实现）

告诉我，我可以：
1. 创建自动迁移脚本
2. 修改代码支持 Keychain
3. 提供完整使用说明

**适合：** 正式使用，中等资金（500-5000U）

### 选项 C：企业级方案（需要额外配置）

**适合：** 生产环境，大额资金（> 5000U）

---

**现在就加固你的安全：**
```bash
chmod 600 .env && echo "✅ 安全加固完成"
```

需要我帮你实现更安全的方案吗？

