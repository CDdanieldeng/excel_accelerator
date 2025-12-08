# Excel/CSV Accelerator

A Python-based tool for automatically detecting table headers and data regions in Excel/CSV files, with REST API backend and Streamlit web frontend. Includes AI-powered chat functionality for data analysis using LangGraph.

## Features

- ✅ Automatic table header row detection
- ✅ Automatic data start row detection
- ✅ Support for multiple file formats: `.xlsx`, `.csv`, `.xlsb`
- ✅ Multi-sheet support with automatic main sheet detection
- ✅ Data preview functionality
- ✅ Sheet image rendering for visual inspection
- ✅ DataFrame building from detected headers
- ✅ AI-powered chat interface for data analysis with LangGraph
- ✅ Intent classification (data analysis, chitchat, unclear)
- ✅ Automatic pandas code generation and execution
- ✅ Excel-friendly thinking steps and explanations
- ✅ File size limits and type validation
- ✅ Encrypted file detection
- ✅ Comprehensive error handling and logging

## Project Structure

```
excel_accelerator/
├── backend/                 # FastAPI backend
│   ├── __init__.py
│   ├── table_render_main.py # Main backend service (port 8000) - includes chat API
│   ├── chatbot_main.py     # Standalone chatbot service (port 8001, legacy)
│   ├── config.py           # Configuration constants
│   ├── logging_config.py   # Logging configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   └── chat_router.py  # Chat with Data API router
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_loader.py  # File loading service
│   │   ├── table_metadata_service.py  # Table metadata management
│   │   ├── table_renderer.py  # Sheet image rendering
│   │   ├── dataframe_builder.py  # DataFrame construction
│   │   ├── dataframe_summary_service.py  # DataFrame summary for LLM
│   │   ├── chat_flow.py    # LangGraph chat flow
│   │   └── llm_service.py  # LLM integration service
│   └── utils/
│       ├── __init__.py
│       └── io_utils.py     # IO utility functions
├── frontend/
│   ├── app.py              # Streamlit frontend application
│   ├── components/
│   │   ├── __init__.py
│   │   ├── upload_page.py  # File upload page
│   │   ├── header_select_page.py  # Header selection page
│   │   └── preview_page.py # Data preview page
│   ├── pages/
│   │   ├── __init__.py
│   │   └── chat_page.py    # Chat interface page
│   └── utils.py            # Frontend utilities
├── requirements.txt        # Python dependencies
├── run_backend.py         # Main backend startup script
├── run_chatbot.py         # Standalone chatbot startup script
└── README.md              # Project documentation
```

## Installation

### 1. Clone or download the project

```bash
cd excel_accelerator
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

Create a `.env` file in the project root:

```bash
# LLM Configuration
LLM_PROVIDER=qwen  # Options: "mock", "chatgpt", "qwen", "local"
QWEN_MODEL=your_model_name
QWEN_API_KEY=your_api_key
QWEN_BASE_URL=your_base_url  # Optional

# File processing limits
MAX_FILE_SIZE_MB=300
MAX_SCAN_ROWS=200
MAX_PREVIEW_ROWS=50
LOG_LEVEL=INFO
```

See `API_KEY_SETUP.md` for detailed LLM API key configuration instructions.

## Running

### Start the main backend service

The main backend provides file processing and Chat with Data functionality:

```bash
# Option 1: Using the startup script (recommended)
python run_backend.py

# Option 2: Using uvicorn directly
uvicorn backend.table_render_main:app --host 0.0.0.0 --port 8000 --reload
```

The backend service will start at `http://localhost:8000` and includes:
- File upload and processing APIs
- Sheet list and image rendering APIs
- DataFrame building API
- Chat with Data API (`/chat/init`, `/chat/message`)

### Start the standalone chatbot service (optional)

The standalone chatbot service is a legacy/alternative implementation:

```bash
# Option 1: Using the startup script
python run_chatbot.py

# Option 2: Using uvicorn directly
uvicorn backend.chatbot_main:app --host 0.0.0.0 --port 8001 --reload
```

The chatbot service will start at `http://localhost:8001` and provides a simple chat endpoint (`/api/chat`).

### Start the frontend service

In another terminal window:

```bash
streamlit run frontend/app.py
```

The frontend will start at `http://localhost:8501`.

## Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:8501`
2. **Upload Page**: Click "Upload Excel/CSV File" and select the file you want to analyze
3. **Header Selection Page**: 
   - Review the detected header row
   - Select the correct header row if needed
   - View sheet images for visual inspection
4. **Preview Page**: 
   - Review the built DataFrame
   - Check column names and data types
   - Preview sample data
5. **Chat Page**: 
   - Ask questions about your data
   - Get AI-powered insights and analysis
   - View generated pandas code

### API Documentation

Once the backend is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Main Backend (port 8000)

#### POST `/api/sheet_list`

Get list of sheets in an uploaded file.

**Request**:
- `file`: File (multipart/form-data)

**Response**:
```json
{
  "file_name": "example.xlsx",
  "file_type": "xlsx",
  "sheets": [
    {
      "name": "Sheet1",
      "is_main": true
    }
  ]
}
```

#### POST `/api/sheet_image`

Get a rendered image of a sheet region.

**Request Parameters**:
- `file`: File (multipart/form-data)
- `sheet_name`: Sheet name (use `__default__` for CSV)
- `row_start`: 0-based start row index (inclusive)
- `row_end`: 0-based end row index (inclusive)
- `col_start`: 0-based start column index (inclusive)
- `col_end`: 0-based end column index (inclusive)

**Response**:
```json
{
  "image_base64": "base64_encoded_image_string"
}
```

#### POST `/api/build_dataframe`

Build a pandas DataFrame from sheet data using a specified header row.

**Request Parameters**:
- `file`: File (multipart/form-data)
- `sheet_name`: Sheet name (use `__default__` for CSV)
- `header_row_number`: Header row number (1-based)
- `max_preview_rows`: Maximum preview rows (default: 100, max: 1000)

**Response**:
```json
{
  "dataset_id": "unique_dataset_id",
  "file_name": "example.xlsx",
  "sheet_name": "Sheet1",
  "header_row_number": 4,
  "n_rows": 100,
  "n_cols": 5,
  "columns": ["Customer Name", "Quantity", "Amount", "Date", "Status"],
  "preview_rows": [
    ["Customer Name", "Quantity", "Amount", "Date", "Status"],
    ["Company A", "10", "100.0", "2024-01-01", "Active"]
  ]
}
```

### Chat with Data API (port 8000)

The Chat with Data API uses LangGraph to provide intelligent data analysis. It includes intent classification, automatic code generation, and execution.

#### POST `/chat/init`

Initialize a chat session for a dataset.

**Request**:
```json
{
  "table_id": "dataset_id_from_build_dataframe",
  "user_id": "optional_user_id"
}
```

**Response**:
```json
{
  "session_id": "unique_session_id",
  "table_schema": {
    "table_id": "dataset_id",
    "n_rows": 100,
    "n_cols": 5,
    "columns": [
      {
        "name": "Customer Name",
        "dtype": "object",
        "chinese_description": null,
        "sample_values": ["Company A", "Company B"],
        "stats": null
      }
    ]
  }
}
```

#### POST `/chat/message`

Send a message in a chat session. The system will:
1. Classify intent (data analysis, chitchat, or unclear)
2. Generate a plan and pandas code
3. Execute the code on the DataFrame
4. Return results with explanations

**Request**:
```json
{
  "session_id": "session_id_from_init",
  "user_query": "What is the total sales amount?",
  "table_id": "optional_table_id_for_session_recovery"
}
```

**Response**:
```json
{
  "final_answer": {
    "text": "总销售额为 $10,000。",
    "pandas_code": "df['Amount'].sum()"
  },
  "thinking_summary": [
    "分析用户查询意图",
    "生成pandas代码",
    "执行代码并格式化结果"
  ],
  "debug": {
    "plan_raw": "分析计划...",
    "bound_plan": "绑定后的计划...",
    "short_explanation": "简短解释..."
  }
}
```

**Note**: Sessions are stored in-memory and will be lost on backend restart. The API supports session recovery if `table_id` is provided in the message request.

### Standalone Chatbot Service (port 8001, legacy)

#### POST `/api/chat`

Simple chat endpoint (legacy/alternative implementation).

**Request**:
```json
{
  "message": "Your question",
  "dataset_id": "optional_dataset_id"
}
```

**Response**:
```json
{
  "response": "Chatbot response text"
}
```

### Health Check

#### GET `/health`

Health check endpoint for both services.

**Response**:
```json
{
  "status": "ok",
  "service": "excel-accelerator"  // or "chatbot"
}
```

## Configuration

The following environment variables can be configured:

### File Processing
- `MAX_FILE_SIZE_MB`: Maximum file size in MB (default: 300)
- `MAX_SCAN_ROWS`: Default maximum scan rows (default: 200)
- `MAX_PREVIEW_ROWS`: Default maximum preview rows (default: 50)

### Logging
- `LOG_LEVEL`: Logging level (default: INFO)

### LLM Configuration
- `LLM_PROVIDER`: LLM provider - options: `"mock"`, `"chatgpt"`, `"qwen"`, `"local"` (default: `"qwen"`)
- `QWEN_MODEL`: Qwen model name (e.g., `"qwen-turbo"`, `"qwen-plus"`) - read by config as `LLM_MODEL`
- `QWEN_API_KEY`: Qwen API key - read by config as `LLM_API_KEY`
- `QWEN_BASE_URL`: Custom Qwen base URL (optional) - read by config as `LLM_BASE_URL`
  - Default: `https://dashscope.aliyuncs.com/compatible-mode/v1`

Example `.env` file:

```bash
# File processing limits
MAX_FILE_SIZE_MB=300
MAX_SCAN_ROWS=200
MAX_PREVIEW_ROWS=50

# Logging
LOG_LEVEL=INFO

# LLM Configuration
LLM_PROVIDER=qwen
QWEN_MODEL=qwen-turbo
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # Optional
```

Or set environment variables directly:

```bash
export MAX_FILE_SIZE_MB=500
export LOG_LEVEL=DEBUG
export LLM_PROVIDER=qwen
export QWEN_MODEL=qwen-turbo
export QWEN_API_KEY=your_key_here
export QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
python run_backend.py
```

## Table Header Detection

The current version uses a heuristic algorithm:

1. Search the first N rows (default: 20, configurable via `MAX_SCAN_ROWS`) for the most likely header row
2. Calculate a "header score" for each row:
   - Rows with high text ratio score higher
   - Rows with high numeric ratio score lower
   - Rows with more non-empty cells get bonus points
3. Select the row with the highest score as the header row
4. Data start row = header row + 1

Users can manually override the detected header row in the web interface.

## Error Handling

The backend handles the following error cases:

- **FILE_TOO_LARGE**: File exceeds size limit
- **UNSUPPORTED_FILE_TYPE**: Unsupported file type
- **FILE_ENCRYPTED**: Detected encrypted/protected file
- **INVALID_RANGE**: Invalid row/column range for sheet image
- **INVALID_REQUEST**: Invalid request parameters
- **TABLE_NOT_FOUND**: Table/dataset not found
- **SESSION_NOT_FOUND**: Chat session not found (supports recovery with `table_id`)
- **FLOW_ERROR**: Error in LangGraph chat flow
- **INTERNAL_ERROR**: Internal processing error
- **NOT_IMPLEMENTED**: Feature not yet implemented

All errors are logged with detailed information (including request_id) for troubleshooting. Error messages are provided in both English and Chinese.

## Logging

Log format includes:
- Timestamp
- Log level
- Module name
- Request ID (for tracking individual requests)
- Message content

Logs are output to stdout and can be redirected to files or processed with log collection tools.

## Development

### Code Style

- Follow PEP 8
- Use type annotations (mypy-friendly)
- Functions and classes have docstrings

### Testing

Run backend tests:

```bash
python test_backend.py
```

### Extension Points

- **Table Metadata Service**: Currently uses in-memory storage. Can be extended to support:
  - Persistent storage (database for metadata, object storage for DataFrames)
  - Data lake integration (S3, HDFS, etc.)
  - Distributed storage for multi-instance deployments
- **Chat Flow**: LangGraph flow can be customized with additional nodes:
  - Custom intent classifiers
  - Additional data analysis tools
  - Excel formula translation
  - Visualization generation
- **LLM Service**: Supports multiple providers (Qwen, ChatGPT, local, mock). Can add:
  - Additional LLM providers (Claude, Gemini, etc.)
  - Custom prompt templates
  - Fine-tuned models
- **File Loader**: Can add support for other formats:
  - Parquet files
  - JSON/JSONL
  - Database connections
- **Table Header Detection**: Algorithm can be further optimized:
  - Machine learning-based detection
  - Multi-row header support
  - Merged cell handling

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit Issues and Pull Requests.

## Chat Flow Architecture

The Chat with Data feature uses LangGraph to orchestrate a multi-step analysis flow:

```
┌─────────────────┐
│  Entry Point    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intent Detector │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    │         │        │
    ▼         ▼        ▼
┌─────────┐ ┌──────────┐  ┌──────────────────┐
│Chitchat │ │Unclear   │  │ Data Analysis   │
│ Handler │ │Handler   │  │ Flow            │
└────┬────┘ └────┬─────┘  └────────┬────────┘
     │           │                 │
     │           │      ┌──────────┴──────────┐
     │           │      │                     │
     │           │      ▼                     ▼
     │           │ ┌──────────┐      ┌──────────────┐
     │           │ │ Planner  │─────▶│ Schema       │
     │           │ │ Node     │      │ Resolver     │
     │           │ └──────────┘      └──────┬───────┘
     │           │                          │
     │           │                          ▼
     │           │                   ┌──────────────┐
     │           │                   │ Code         │
     │           │                   │ Generator    │
     │           │                   └──────┬───────┘
     │           │                          │
     │           │                          ▼
     │           │                   ┌──────────────┐
     │           │                   │ Code         │
     │           │                   │ Executor     │
     │           │                   └──────┬───────┘
     │           │                          │
     │           │                          ▼
     │           │                   ┌──────────────┐
     │           │                   │ Excel        │
     │           │                   │ Translator   │
     │           │                   └──────┬───────┘
     │           │                          │
     │           │                          ▼
     │           │                   ┌──────────────┐
     │           │                   │ Result       │
     │           │                   │ Explainer    │
     │           │                   └──────┬───────┘
     │           │                          │
     └───────────┴──────────────────────────┴───┐
                                                │
                                                ▼
                                         ┌──────────┐
                                         │   END    │
                                         └──────────┘
```

### Flow Steps

1. **Intent Classification**: Determines if the query is data analysis, chitchat, or unclear
2. **Planner Node**: Generates an analysis plan based on the query
3. **Schema Resolver**: Resolves column names and validates against the DataFrame schema
4. **Code Generator**: Generates pandas code to answer the query
5. **Code Executor**: Safely executes the pandas code on the DataFrame
6. **Excel Translator**: Converts pandas operations to Excel-friendly explanations
7. **Result Explainer**: Formats the results with natural language explanations

The flow includes error handling, retry logic, and clarification requests for unclear queries.