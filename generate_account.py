"""
生成 Hyperliquid 测试账户

这个脚本会生成一个新的以太坊兼容账户，可用于 Hyperliquid 测试网。
"""
from eth_account import Account
import secrets


def generate_account():
    """生成新账户"""
    # 生成随机私钥
    priv_key = "0x" + secrets.token_hex(32)
    
    # 创建账户
    account = Account.from_key(priv_key)
    
    return {
        "address": account.address,
        "private_key": priv_key
    }


def main():
    print("=" * 70)
    print("🔐 Hyperliquid 测试账户生成器")
    print("=" * 70)
    print()
    
    # 生成账户
    account = generate_account()
    
    print("✅ 已生成新的测试账户：")
    print()
    print("📍 钱包地址：")
    print(f"   {account['address']}")
    print()
    print("🔑 私钥（请妥善保管）：")
    print(f"   {account['private_key']}")
    print()
    print("=" * 70)
    print("⚠️  重要提示：")
    print("=" * 70)
    print()
    print("1. 这是一个全新生成的账户，仅用于测试网")
    print("2. 请将私钥保存到 .env 文件中：")
    print(f"   HYPERLIQUID_PRIVATE_KEY={account['private_key']}")
    print()
    print("3. 确保 .env 文件中设置：")
    print("   HYPERLIQUID_TESTNET=true")
    print()
    print("4. 获取测试网代币：")
    print("   访问 Hyperliquid 测试网水龙头获取测试 USDC")
    print("   测试网网址: https://app.hyperliquid-testnet.xyz")
    print()
    print("5. 永远不要在主网使用测试账户的私钥！")
    print()
    print("=" * 70)
    
    # 询问是否写入 .env 文件
    response = input("\n是否要自动更新 .env 文件？(y/n): ").strip().lower()
    
    if response == 'y':
        try:
            # 读取现有 .env 文件或创建新文件
            try:
                with open('.env', 'r') as f:
                    lines = f.readlines()
            except FileNotFoundError:
                # 如果 .env 不存在，从 .env.example 复制
                try:
                    with open('.env.example', 'r') as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    lines = []
            
            # 更新私钥
            updated = False
            new_lines = []
            
            for line in lines:
                if line.startswith('HYPERLIQUID_PRIVATE_KEY='):
                    new_lines.append(f'HYPERLIQUID_PRIVATE_KEY={account["private_key"]}\n')
                    updated = True
                elif line.startswith('HYPERLIQUID_TESTNET='):
                    new_lines.append('HYPERLIQUID_TESTNET=true\n')
                else:
                    new_lines.append(line)
            
            # 如果没有找到私钥行，添加一个
            if not updated:
                new_lines.append(f'\nHYPERLIQUID_PRIVATE_KEY={account["private_key"]}\n')
                new_lines.append('HYPERLIQUID_TESTNET=true\n')
            
            # 写入 .env 文件
            with open('.env', 'w') as f:
                f.writelines(new_lines)
            
            print("\n✅ 已更新 .env 文件！")
            print("现在可以运行 python main.py 启动系统")
            
        except Exception as e:
            print(f"\n❌ 更新 .env 文件失败: {e}")
            print("请手动将私钥添加到 .env 文件中")
    else:
        print("\n请手动将私钥添加到 .env 文件中")
    
    print()


if __name__ == "__main__":
    main()

