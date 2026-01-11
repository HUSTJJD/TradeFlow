import os
import ast
import glob
from typing import List, Dict, Any

def parse_file(filepath: str) -> Dict[str, Any]:
    """解析 Python 文件，提取类和函数信息"""
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return {}

    module_doc = ast.get_docstring(tree)
    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "doc": ast.get_docstring(node),
                "methods": [],
                "bases": [base.id for base in node.bases if isinstance(base, ast.Name)]
            }
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_info = {
                        "name": item.name,
                        "doc": ast.get_docstring(item),
                        "args": [arg.arg for arg in item.args.args],
                        "returns": _get_annotation(item.returns)
                    }
                    class_info["methods"].append(method_info)
            classes.append(class_info)
        elif isinstance(node, ast.FunctionDef):
            func_info = {
                "name": node.name,
                "doc": ast.get_docstring(node),
                "args": [arg.arg for arg in node.args.args],
                "returns": _get_annotation(node.returns)
            }
            functions.append(func_info)

    return {
        "filepath": filepath,
        "doc": module_doc,
        "classes": classes,
        "functions": functions
    }

def _get_annotation(node) -> str:
    """获取类型注解的字符串表示"""
    if node is None:
        return "None"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Subscript):
        value = _get_annotation(node.value)
        slice_val = _get_annotation(node.slice)
        return f"{value}[{slice_val}]"
    return "Any"

def generate_markdown(parsed_data: List[Dict[str, Any]]) -> str:
    """生成 Markdown 文档"""
    md = "# TradeFlow 项目 AI 文档\n\n本文档由脚本自动生成，旨在帮助 AI 理解项目结构和代码逻辑。\n\n"

    for data in parsed_data:
        if not data:
            continue

        rel_path = os.path.relpath(data["filepath"], os.getcwd())
        md += f"## 文件: `{rel_path}`\n\n"

        if data["doc"]:
            md += f"{data['doc']}\n\n"

        if data["classes"]:
            md += "### 类\n\n"
            for cls in data["classes"]:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                md += f"#### `class {cls['name']}{bases}`\n\n"
                if cls["doc"]:
                    md += f"{cls['doc']}\n\n"

                if cls["methods"]:
                    md += "**方法:**\n\n"
                    for method in cls["methods"]:
                        args = ", ".join(method["args"])
                        md += f"- `{method['name']}({args}) -> {method['returns']}`\n"
                        if method["doc"]:
                            # 提取第一行作为简述
                            summary = method["doc"].split('\n')[0]
                            md += f"  - {summary}\n"
                    md += "\n"

        if data["functions"]:
            md += "### 函数\n\n"
            for func in data["functions"]:
                args = ", ".join(func["args"])
                md += f"#### `def {func['name']}({args}) -> {func['returns']}`\n\n"
                if func["doc"]:
                    md += f"{func['doc']}\n\n"

        md += "---\n\n"

    return md

def main():
    root_dir = "app"
    files = glob.glob(os.path.join(root_dir, "**", "*.py"), recursive=True)

    parsed_data = []
    for file in files:
        if "__init__.py" in file:
            continue
        print(f"正在解析: {file}")
        parsed_data.append(parse_file(file))

    md_content = generate_markdown(parsed_data)

    with open("DOC.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("文档生成完成: DOC.md")

if __name__ == "__main__":
    main()
