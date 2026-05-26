# Excel Agent Studio Backend

## 项目介绍

后端使用 FastAPI + LangGraph + openpyxl/pandas，实现本地 Excel Agent MVP：

- 接收自然语言和可选 `.xlsx` 上传
- 分析已上传工作簿结构
- 调用 DeepSeek OpenAI-compatible API 生成结构化 `ExcelPlan`
- 校验计划后等待用户确认
- 由稳定工具函数真实生成或修改 Excel
- 校验输出工作簿并提供下载

## 后端启动方式

macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Windows:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## .env 配置说明

- `DEEPSEEK_API_KEY`: DeepSeek API Key，必填
- `DEEPSEEK_BASE_URL`: DeepSeek OpenAI-compatible API 地址，默认 `https://api.deepseek.com/v1`
- `DEEPSEEK_MODEL`: 模型名，默认 `deepseek-chat`
- `USE_MOCK_LLM`: 设为 `true` 时不调用 DeepSeek，返回固定可执行 ExcelPlan

## DeepSeek API 配置说明

`planner_node` 使用 OpenAI SDK 调用 DeepSeek，并强制：

- `response_format={"type":"json_object"}`
- 系统提示词只允许返回 JSON
- 返回结果必须能被 `ExcelPlan` Pydantic schema 校验

如果未配置 `DEEPSEEK_API_KEY`，创建任务会返回清晰错误，任务状态会标记为 `failed`。

## MVP 支持能力

- 仅支持 `.xlsx`
- 新建工作簿
- 基于现有 `.xlsx` 修改并另存为新文件
- 工作簿结构分析
- 创建 sheet
- 追加列
- 创建汇总 sheet
- 基础格式化：表头加粗、冻结首行、自动筛选、自动列宽
- 简单公式写入
- 任务 JSON 持久化

## 当前不支持的能力

- `.xls`
- VBA / 宏
- 数据透视表
- Office 插件
- 直接控制本地 Excel 软件
- 执行 LLM 生成 Python 代码
- 登录注册、权限系统、云端部署

## 测试用例

1. 不上传文件，生成“药店终端拜访记录表”，确认：
   - 任务状态进入 `waiting_confirm`
   - 确认后能下载 `.xlsx`
   - 至少包含明细 sheet 和汇总 sheet
2. 上传销售明细表，生成按部门汇总的 sheet，确认：
   - 能返回 workbook_context
   - 确认后生成新文件
   - 原上传文件不被覆盖
3. 上传普通表格，要求正式化格式，确认：
   - 计划中包含 `format_sheet` 或 style
   - 输出文件表头加粗、冻结首行、自动筛选、自动列宽
