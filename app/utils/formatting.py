import unicodedata


def get_display_width(s: str) -> int:
    """计算字符串的显示宽度（东亚宽度）。"""
    width = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width


def pad_string(s: str, width: int, align: str = "<") -> str:
    """
    用空格填充字符串以达到目标显示宽度。
    align: '<' 左对齐 (默认), '>' 右对齐
    """
    current_width = get_display_width(s)
    padding = width - current_width
    if padding > 0:
        if align == ">":
            return " " * padding + s
        else:
            return s + " " * padding
    return s
