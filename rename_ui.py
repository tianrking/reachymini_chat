import os
import re

def customize_seeed_ui(ui_dir):
    """
    修改 Pipecat 官方 UI 为 Seeed Studio
    以一种开发者可读且易于维护的方式进行
    """
    # 1. 修改 HTML 标题
    index_html = os.path.join(ui_dir, "index.html")
    if os.path.exists(index_html):
        with open(index_html, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("<title>Pipecat UI</title>", "<title>Seeed Studio AI Bot</title>")
        with open(index_html, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已更新 HTML 标题: {index_html}")

    # 2. 修改 JS 文件中的品牌名
    # 我们搜索 "Pipecat Playground" 并替换为 "Seeed Studio"
    assets_dir = os.path.join(ui_dir, "assets")
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith(".js"):
                filepath = os.path.join(assets_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 同时也处理可能的重复 Studio 问题
                new_content = content.replace("Pipecat Playground", "Seeed Studio")
                new_content = new_content.replace("Pipecat", "Seeed Studio")
                
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"✅ 已更新 JS 品牌文本: {filename}")

if __name__ == "__main__":
    ui_path = os.path.join(os.path.dirname(__file__), "custom_ui")
    customize_seeed_ui(ui_path)
