# Excel/CSV 表头自动猜测工具

一个基于 Python 的 Excel/CSV 表头与数据主体自动检测工具，提供 REST API 后端和 Streamlit Web 前端。

## 功能特性

- ✅ 自动检测表头行索引
- ✅ 自动检测数据起始行索引
- ✅ 支持多种文件格式：`.xlsx`, `.csv`, `.xlsb`
- ✅ 多 Sheet 支持（自动识别主表）
- ✅ 数据预览功能
- ✅ 文件大小限制和类型校验
- ✅ 加密文件检测
- ✅ 完整的错误处理和日志记录

## 项目结构

```
excel_accelerator/
├── backend/                 # FastAPI 后端
│   ├── __init__.py
│   ├── main.py             # FastAPI 应用入口
│   ├── config.py           # 配置常量
│   ├── logging_config.py   # 日志配置
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic 模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_loader.py  # 文件加载服务
│   │   └── table_detector.py  # 表头检测服务
│   └── utils/
│       ├── __init__.py
│       └── io_utils.py     # IO 工具函数
├── frontend/
│   └── app.py              # Streamlit 前端
├── requirements.txt        # Python 依赖
└── README.md              # 项目文档
```

## 安装

### 1. 克隆或下载项目

```bash
cd excel_accelerator
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

### 启动后端服务

```bash
# 方式 1: 使用 uvicorn 直接运行
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 方式 2: 使用 Python 运行
python -m backend.main
```

后端服务将在 `http://localhost:8000` 启动。

### 启动前端服务

在另一个终端窗口中：

```bash
streamlit run frontend/app.py
```

前端将在 `http://localhost:8501` 启动。

## 使用说明

1. 打开浏览器访问 `http://localhost:8501`
2. 点击"上传 Excel/CSV 文件"按钮，选择要分析的文件
3. 在侧边栏配置预览行数和扫描行数（可选）
4. 点击"开始分析"按钮
5. 查看检测结果：
   - 表头行索引（显示为第 X 行）
   - 数据起始行索引
   - 检测到的列名
   - 数据预览表格

## API 文档

后端启动后，可以访问：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要 API 端点

#### POST `/api/guess_table`

分析上传的文件并检测表头。

**请求参数**:
- `file`: 文件（multipart/form-data）
- `max_preview_rows` (query, optional): 最大预览行数，默认 50
- `max_scan_rows` (query, optional): 最大扫描行数，默认 200

**响应示例**:

```json
{
  "file_name": "example.xlsx",
  "file_type": "xlsx",
  "sheets": [
    {
      "name": "Sheet1",
      "is_main": true,
      "header_row_index": 4,
      "data_start_row_index": 5,
      "detected_columns": ["客户名称", "数量", "金额"],
      "preview": {
        "rows": [
          ["客户名称", "数量", "金额"],
          ["A公司", "10", "100.0"]
        ]
      }
    }
  ]
}
```

## 配置

可以通过环境变量配置以下参数：

- `MAX_FILE_SIZE_MB`: 最大文件大小（MB），默认 300
- `MAX_HEADER_SEARCH_ROWS`: 表头搜索最大行数，默认 20
- `MAX_SCAN_ROWS`: 默认最大扫描行数，默认 200
- `MAX_PREVIEW_ROWS`: 默认最大预览行数，默认 50
- `LOG_LEVEL`: 日志级别，默认 INFO

示例：

```bash
export MAX_FILE_SIZE_MB=500
export LOG_LEVEL=DEBUG
uvicorn backend.main:app --reload
```

## 表头检测算法

当前版本使用简单的启发式算法：

1. 在前 N 行（默认 20 行）中搜索最可能的表头行
2. 对每行计算"表头得分"：
   - 文本比例高的行得分更高
   - 数字比例高的行得分更低
   - 非空单元格数量多的行有加分
3. 选择得分最高的行作为表头行
4. 数据起始行 = 表头行 + 1

## 错误处理

后端会处理以下错误情况：

- **FILE_TOO_LARGE**: 文件超过大小限制
- **UNSUPPORTED_FILE_TYPE**: 不支持的文件类型
- **FILE_ENCRYPTED**: 检测到加密/受保护文件
- **INTERNAL_ERROR**: 内部处理错误

所有错误都会记录详细日志（包含 request_id），便于排查问题。

## 日志

日志格式包含：
- 时间戳
- 日志级别
- 模块名
- request_id（用于追踪单个请求）
- 消息内容

日志输出到标准输出，可以通过重定向到文件或使用日志收集工具处理。

## 开发说明

### 代码风格

- 遵循 PEP 8
- 使用类型注解（mypy 友好）
- 函数和类都有文档字符串

### 扩展点

- `TableDetector`: 可以扩展支持多级表头、多表块检测
- `file_loader`: 可以添加对其他格式的支持（如 parquet）
- 表头检测算法可以进一步优化

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

