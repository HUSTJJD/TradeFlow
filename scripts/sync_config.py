import re
import os
import sys

# 配置敏感字段及其占位符和所属 section
# 格式: 'field_name': {'section': 'section_name', 'placeholder': 'placeholder_value'}
SENSITIVE_CONFIG = {
    "app_key": {"section": "longport", "placeholder": "YOUR_APP_KEY"},
    "app_secret": {"section": "longport", "placeholder": "YOUR_APP_SECRET"},
    "access_token": {"section": "longport", "placeholder": "YOUR_ACCESS_TOKEN"},
    "smtp_server": {"section": "email", "placeholder": "smtp.example.com"},
    "smtp_port": {"section": "email", "placeholder": 465},
    "sender_email": {
        "section": "email",
        "placeholder": "your_email@example.com",
    },
    "sender_password": {"section": "email", "placeholder": "your_password"},
    "receiver_emails": {
        "section": "email",
        "placeholder": ["receiver@example.com"],
    },
}

def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sync_config():
    base_dir = get_project_root()
    source_file = os.path.join(base_dir, 'config', 'config.yaml')
    target_file = os.path.join(base_dir, 'config', 'config.yaml.example')

    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {source_file}: {e}")
        return

    new_lines = []
    current_section = None
    
    # 简单的层级解析：假设 section 是顶层，无缩进
    section_pattern = re.compile(r'^(\w+):')
    key_pattern = re.compile(r'^(\s+)(\w+):')

    skip_list_items = False
    last_key_indent_len = 0

    for line in lines:
        # 如果处于跳过列表项模式
        if skip_list_items:
            # 计算当前行缩进
            current_indent_match = re.match(r'^(\s+)', line)
            current_indent_len = len(current_indent_match.group(1)) if current_indent_match else 0
            
            # 如果是空行，保留
            if line.strip() == '':
                new_lines.append(line)
                continue
            
            # 如果缩进比上一个key深，且以 - 开头，说明是列表项，跳过
            if current_indent_len > last_key_indent_len and line.strip().startswith('-'):
                continue
            else:
                # 结束跳过模式
                skip_list_items = False

        # 检查是否是 section
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1)
            new_lines.append(line)
            skip_list_items = False
            continue

        # 检查是否是 key
        key_match = key_pattern.match(line)
        if key_match:
            indent = key_match.group(1)
            key = key_match.group(2)
            
            if key in SENSITIVE_CONFIG:
                config = SENSITIVE_CONFIG[key]
                # 检查 section 是否匹配
                if config['section'] == current_section:
                    # 替换值，保留注释
                    # 查找冒号后的部分
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        value_part = parts[1]
                        # 检查是否有注释
                        comment_match = re.search(r'(\s*#.*)$', value_part)
                        comment = comment_match.group(1) if comment_match else ''
                        
                        # 构建新行
                        placeholder = config['placeholder']
                        if isinstance(placeholder, str):
                            if placeholder:
                                new_line = f"{indent}{key}: \"{placeholder}\"{comment}\n"
                            else:
                                new_line = f"{indent}{key}: \"\"{comment}\n"
                        else:
                            new_line = f"{indent}{key}: {placeholder}{comment}\n"
                        new_lines.append(new_line)
                        
                        # 标记可能需要跳过后续列表项
                        skip_list_items = True
                        last_key_indent_len = len(indent)
                        continue
        
        # 其他情况直接保留
        new_lines.append(line)

    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Synced {source_file} to {target_file} with masked sensitive data.")
    except Exception as e:
        print(f"Error writing to {target_file}: {e}")

def install_hook():
    base_dir = get_project_root()
    git_dir = os.path.join(base_dir, '.git')
    
    if not os.path.exists(git_dir):
        print("Error: .git directory not found. Is this a git repository?")
        return

    hook_dir = os.path.join(git_dir, 'hooks')
    if not os.path.exists(hook_dir):
        os.makedirs(hook_dir)

    hook_path = os.path.join(hook_dir, 'pre-commit')

    # 写入 hook 内容
    # 使用 python 运行当前脚本
    hook_content = """#!/bin/sh
# Auto-sync config.yaml to config.yaml.example
echo "Syncing config.yaml to config.yaml.example..."
python scripts/sync_config.py
git add config/config.yaml.example
"""
    
    try:
        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(hook_content)
        
        # 尝试设置可执行权限
        try:
            import stat
            st = os.stat(hook_path)
            os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
        except Exception:
            pass # Windows 上可能不需要或失败
        
        print(f"Git pre-commit hook installed to {hook_path}")
    except Exception as e:
        print(f"Failed to install hook: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--install':
        install_hook()
    else:
        sync_config()
