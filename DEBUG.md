# 后端调试指南

本文档说明如何独立运行和调试后端服务。

## 🚀 快速测试表头检测（推荐）

如果你想直接测试表头检测功能，不需要启动 API 服务：

```bash
# 基本用法
python test_detector.py <文件路径>

# 示例
python test_detector.py test.xlsx
python test_detector.py data.csv

# 自定义参数
python test_detector.py test.xlsx 500 100
# 参数说明: 文件路径 最大扫描行数 最大预览行数
```

这个脚本会：
- ✅ 直接加载文件
- ✅ 检测表头行和数据起始行
- ✅ 显示检测到的列名
- ✅ 显示数据预览
- ✅ 标记主表

**无需启动后端服务，直接运行即可！**

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端服务

#### 方式 1: 使用提供的脚本（推荐）

```bash
python run_backend.py
```

#### 方式 2: 使用 uvicorn 命令

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 方式 3: 直接运行 main.py

```bash
python -m backend.main
```

### 3. 验证服务运行

服务启动后，访问以下地址：

- **健康检查**: http://localhost:8000/health
- **API 文档 (Swagger)**: http://localhost:8000/docs
- **API 文档 (ReDoc)**: http://localhost:8000/redoc

## 测试 API

### 使用测试脚本

```bash
# 只测试健康检查
python test_backend.py --health-only

# 测试文件分析
python test_backend.py --file <文件路径>

# 自定义参数
python test_backend.py --file test.xlsx --max-preview-rows 100 --max-scan-rows 500
```

### 使用 curl

```bash
# 健康检查
curl http://localhost:8000/health

# 上传文件分析
curl -X POST "http://localhost:8000/api/guess_table?max_preview_rows=50&max_scan_rows=200" \
  -F "file=@test.xlsx"
```

### 使用 Python requests

```python
import requests

# 上传文件
with open("test.xlsx", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/guess_table",
        files={"file": f},
        params={"max_preview_rows": 50, "max_scan_rows": 200}
    )
    print(response.json())
```

## 调试技巧

### 1. 查看日志

后端服务会在控制台输出详细日志，包括：
- 请求 ID（用于追踪单个请求）
- 文件验证信息
- 文件加载进度
- 表头检测结果

### 2. 设置日志级别

通过环境变量设置日志级别：

```bash
# DEBUG 级别（最详细）
export LOG_LEVEL=DEBUG
python run_backend.py

# INFO 级别（默认）
export LOG_LEVEL=INFO
python run_backend.py

# WARNING 级别（只显示警告和错误）
export LOG_LEVEL=WARNING
python run_backend.py
```

### 3. 使用 Python 调试器

在代码中添加断点：

```python
import pdb; pdb.set_trace()
```

或使用 IDE 的调试功能（如 VS Code、PyCharm）。

### 4. 测试单个组件

#### 测试文件加载器

```python
from backend.services.file_loader import load_file_sample

samples = load_file_sample("test.xlsx", "xlsx", max_scan_rows=200)
for sample in samples:
    print(f"Sheet: {sample.name}, Rows: {len(sample.rows)}")
```

#### 测试表头检测器

```python
from backend.services.table_detector import TableDetector
from backend.services.file_loader import load_file_sample

# 加载文件
samples = load_file_sample("test.xlsx", "xlsx", max_scan_rows=200)

# 检测表头
detector = TableDetector()
for sample in samples:
    result = detector.detect_sheet(sample.name, sample.rows, max_preview_rows=50)
    print(f"Sheet: {result.name}")
    print(f"Header row: {result.header_row_index}")
    print(f"Data start: {result.data_start_row_index}")
    print(f"Columns: {result.detected_columns}")
```

### 5. 常见问题排查

#### 问题: 端口被占用

```bash
# 查看端口占用
lsof -i :8000

# 或使用其他端口
uvicorn backend.main:app --port 8001
```

#### 问题: 导入错误

确保在项目根目录运行，或设置 PYTHONPATH：

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python run_backend.py
```

#### 问题: 文件读取失败

检查：
1. 文件路径是否正确
2. 文件格式是否支持（xlsx, csv, xlsb）
3. 文件是否加密（加密文件会被拒绝）
4. 文件大小是否超过限制（默认 300MB）

#### 问题: 表头检测不准确

可以：
1. 增加 `max_scan_rows` 参数
2. 调整 `MAX_HEADER_SEARCH_ROWS` 配置
3. 查看日志中的 header_score 信息（DEBUG 级别）

## 配置参数

可以通过环境变量配置：

```bash
# 文件大小限制（MB）
export MAX_FILE_SIZE_MB=500

# 表头搜索最大行数
export MAX_HEADER_SEARCH_ROWS=30

# 默认最大扫描行数
export MAX_SCAN_ROWS=500

# 默认最大预览行数
export MAX_PREVIEW_ROWS=100

# 日志级别
export LOG_LEVEL=DEBUG
```

## 性能分析

### 使用 cProfile

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 运行你的代码
# ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 显示前 20 个最耗时的函数
```

### 使用 line_profiler

安装：
```bash
pip install line_profiler
```

使用：
```python
@profile
def your_function():
    # ...
    pass
```

运行：
```bash
kernprof -l -v your_script.py
```

## 下一步

- 查看 `README.md` 了解完整功能
- 查看 API 文档: http://localhost:8000/docs
- 查看源代码注释了解实现细节

