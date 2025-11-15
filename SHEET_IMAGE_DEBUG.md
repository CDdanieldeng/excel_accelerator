# Sheet 图片渲染功能调试指南

## 快速开始

### 1. 安装依赖

```bash
# 确保安装了所有依赖，特别是 Pillow
pip install -r requirements.txt
```

### 2. 准备测试文件

准备一个测试用的 Excel 或 CSV 文件，例如：
- `test.xlsx` - 包含一些数据的 Excel 文件
- `test.csv` - CSV 文件

### 3. 启动后端服务

```bash
# 方式 1: 使用脚本
python run_backend.py

# 方式 2: 使用 uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

后端启动后，你应该看到：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 4. 启动前端服务

在新的终端窗口中：

```bash
streamlit run frontend/app.py
```

前端会在 `http://localhost:8501` 启动。

## 调试步骤

### 方式 1: 使用前端界面（推荐）

1. 打开浏览器访问 `http://localhost:8501`
2. 在侧边栏选择 **"Sheet 图片渲染"**
3. 填写表单：
   - **文件路径**: 输入完整路径，例如 `/Users/yourname/Desktop/test.xlsx`
   - **Sheet 名称**: 例如 `Sheet1`（CSV 使用 `__default__`）
   - **行列范围**: 设置要渲染的范围
4. 点击 **"🚀 渲染图片"** 按钮
5. 查看结果和错误信息

### 方式 2: 使用 curl 测试 API

```bash
# 基本测试
curl "http://localhost:8000/api/sheet_image?file_path=/path/to/test.xlsx&sheet_name=Sheet1&row_start=0&row_end=10&col_start=0&col_end=5"

# 保存响应到文件查看
curl "http://localhost:8000/api/sheet_image?file_path=/path/to/test.xlsx&sheet_name=Sheet1&row_start=0&row_end=10&col_start=0&col_end=5" > response.json

# 查看 JSON 响应
cat response.json | python -m json.tool
```

### 方式 3: 使用 Python 脚本测试

创建一个测试脚本 `test_sheet_image.py`:

```python
#!/usr/bin/env python3
import requests
import base64
import io
from PIL import Image

# API 参数
url = "http://localhost:8000/api/sheet_image"
params = {
    "file_path": "/path/to/test.xlsx",  # 替换为你的文件路径
    "sheet_name": "Sheet1",
    "row_start": 0,
    "row_end": 10,
    "col_start": 0,
    "col_end": 5,
}

# 发送请求
response = requests.get(url, params=params)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    
    # 解码图片
    image_base64 = result["image_base64"]
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_bytes))
    
    # 保存图片
    image.save("output.png")
    print(f"✅ 图片已保存到 output.png")
    print(f"图片大小: {image.width} x {image.height}")
    print(f"行高: {result['row_height_px']} px")
    print(f"列宽: {result['col_width_px']} px")
else:
    print(f"❌ 错误: {response.json()}")
```

运行：
```bash
python test_sheet_image.py
```

## 查看日志

### 后端日志

后端服务会在控制台输出详细日志，包括：
- 请求 ID（用于追踪单个请求）
- 文件路径和 sheet 名称
- 行列范围
- 加载和渲染进度
- 错误信息

**示例日志输出：**
```
2024-01-01 10:00:00 | INFO     | backend.main | [request_id=abc123] | Sheet image request: file_path=/path/to/test.xlsx, sheet_name=Sheet1, rows=[0, 10], cols=[0, 5]
2024-01-01 10:00:00 | INFO     | backend.services.table_renderer | [request_id=abc123] | Loading sheet window: file=/path/to/test.xlsx, sheet=Sheet1, rows=[0, 10], cols=[0, 5]
2024-01-01 10:00:01 | INFO     | backend.services.table_renderer | [request_id=abc123] | Loaded XLSX window: 11 rows, 6 columns
2024-01-01 10:00:01 | INFO     | backend.services.table_renderer | [request_id=abc123] | Rendering grid: 11 rows x 6 cols, image size: 630x264 pixels
2024-01-01 10:00:01 | INFO     | backend.services.table_renderer | [request_id=abc123] | Rendered PNG: 15234 bytes
```

### 启用 DEBUG 日志

```bash
# 设置环境变量
export LOG_LEVEL=DEBUG

# 然后启动后端
python run_backend.py
```

## 常见问题排查

### 问题 1: 文件不存在

**错误信息：**
```
❌ 错误代码: FILE_NOT_FOUND
错误信息: 文件不存在: /path/to/file.xlsx
```

**解决方案：**
- 检查文件路径是否正确（使用绝对路径）
- 确认文件确实存在
- 检查文件权限

**测试文件路径：**
```python
import os
file_path = "/path/to/test.xlsx"
print(f"文件存在: {os.path.exists(file_path)}")
print(f"文件路径: {os.path.abspath(file_path)}")
```

### 问题 2: Sheet 不存在

**错误信息：**
```
❌ 错误代码: INVALID_REQUEST
错误信息: 无效的请求: Sheet 'Sheet1' not found in file
```

**解决方案：**
- 检查 sheet 名称是否正确（区分大小写）
- 列出文件中的所有 sheet：
  ```python
  from openpyxl import load_workbook
  wb = load_workbook("test.xlsx", read_only=True)
  print("Sheet 列表:", wb.sheetnames)
  wb.close()
  ```

### 问题 3: 范围无效

**错误信息：**
```
❌ 错误代码: INVALID_RANGE
错误信息: row_end (10) must be >= row_start (20)
```

**解决方案：**
- 确保 `row_end >= row_start`
- 确保 `col_end >= col_start`
- 检查索引是否从 0 开始

### 问题 4: 连接错误

**错误信息：**
```
❌ 连接错误: 无法连接到后端服务
```

**解决方案：**
- 确认后端服务正在运行
- 检查端口 8000 是否被占用：
  ```bash
  lsof -i :8000
  ```
- 检查后端地址是否正确（默认 `http://localhost:8000`）

### 问题 5: 图片渲染失败

**可能原因：**
- Pillow 未正确安装
- 字体加载失败（会回退到默认字体）
- 内存不足（处理大文件时）

**解决方案：**
```bash
# 重新安装 Pillow
pip install --upgrade Pillow

# 检查 Pillow 版本
python -c "from PIL import Image; print(Image.__version__)"
```

### 问题 6: 不支持的文件格式

**错误信息：**
```
❌ 错误代码: NOT_IMPLEMENTED
错误信息: 功能尚未实现: xlsb format is not yet supported
```

**解决方案：**
- xlsb 格式暂时不支持
- 使用 xlsx 或 csv 格式

## 调试技巧

### 1. 测试单个组件

#### 测试数据加载

```python
from backend.services.table_renderer import load_sheet_window

grid = load_sheet_window(
    file_path="/path/to/test.xlsx",
    sheet_name="Sheet1",
    row_start=0,
    row_end=10,
    col_start=0,
    col_end=5,
)

print(f"加载了 {len(grid)} 行")
for i, row in enumerate(grid[:3]):  # 显示前 3 行
    print(f"行 {i}: {row}")
```

#### 测试图片渲染

```python
from backend.services.table_renderer import TableImageRenderer, load_sheet_window

# 加载数据
grid = load_sheet_window(
    file_path="/path/to/test.xlsx",
    sheet_name="Sheet1",
    row_start=0,
    row_end=10,
    col_start=0,
    col_end=5,
)

# 渲染
renderer = TableImageRenderer()
png_bytes, row_height, col_width = renderer.render_grid(grid, row_offset=0, col_offset=0)

# 保存图片
with open("test_output.png", "wb") as f:
    f.write(png_bytes)

print(f"图片已保存: {len(png_bytes)} bytes")
print(f"行高: {row_height} px, 列宽: {col_width} px")
```

### 2. 使用断点调试

在代码中添加断点：

```python
import pdb; pdb.set_trace()
```

或使用 IDE 的调试功能（VS Code、PyCharm 等）。

### 3. 检查中间结果

在 `table_renderer.py` 中添加临时日志：

```python
logger.debug(f"Grid shape: {len(grid)} rows x {max(len(r) for r in grid) if grid else 0} cols")
logger.debug(f"First row: {grid[0] if grid else 'empty'}")
```

### 4. 验证 API 响应

```python
import requests
import json

response = requests.get(
    "http://localhost:8000/api/sheet_image",
    params={
        "file_path": "/path/to/test.xlsx",
        "sheet_name": "Sheet1",
        "row_start": 0,
        "row_end": 10,
        "col_start": 0,
        "col_end": 5,
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
```

## 性能测试

### 测试不同大小的数据窗口

```python
import time
import requests

sizes = [
    (0, 10, 0, 5),    # 小
    (0, 50, 0, 10),   # 中
    (0, 100, 0, 20),  # 大
]

for row_start, row_end, col_start, col_end in sizes:
    start_time = time.time()
    
    response = requests.get(
        "http://localhost:8000/api/sheet_image",
        params={
            "file_path": "/path/to/test.xlsx",
            "sheet_name": "Sheet1",
            "row_start": row_start,
            "row_end": row_end,
            "col_start": col_start,
            "col_end": col_end,
        }
    )
    
    elapsed = time.time() - start_time
    print(f"范围 [{row_start}-{row_end}, {col_start}-{col_end}]: {elapsed:.2f}秒, 状态: {response.status_code}")
```

## 下一步

- 查看 API 文档: http://localhost:8000/docs
- 测试不同的文件格式和大小
- 验证图片质量和像素映射准确性
- 根据需要调整渲染参数（行高、列宽、字体等）

