# Excel Agent Studio

## 项目介绍

Excel Agent Studio 是一个本地 Web 版 Excel Agent MVP。用户可以输入自然语言来生成 `.xlsx` 文件，也可以上传已有 `.xlsx` 后要求系统进行修改。后端用 LangGraph 编排流程，DeepSeek API 只负责输出结构化 `ExcelPlan JSON`，真正的 Excel 读写由 `openpyxl` 和 `pandas` 工具层完成。

## 项目结构

```text
excel-agent-studio/
  backend/
  frontend/
```

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

## 前端启动方式

```bash
cd frontend
npm install
npm run dev
```

## .env 配置说明

在 `backend/.env` 中配置：

- `DEEPSEEK_API_KEY`: DeepSeek API Key，必填
- `DEEPSEEK_BASE_URL`: DeepSeek OpenAI-compatible 地址，默认 `https://api.deepseek.com/v1`
- `DEEPSEEK_MODEL`: 模型名，默认 `deepseek-chat`
- `USE_MOCK_LLM`: 设为 `true` 时不调用 DeepSeek，返回固定可执行 ExcelPlan

## DeepSeek API 配置说明

- 项目通过 OpenAI SDK 连接 DeepSeek OpenAI-compatible API
- `planner_node` 强制要求 `response_format={"type":"json_object"}`
- 系统提示词明确限制只能输出 JSON
- 未配置 API Key 时，任务会失败并返回清晰错误

## MVP 支持能力

- 仅支持 `.xlsx`
- 创建新工作簿
- 上传现有 `.xlsx` 后生成修改计划
- 读取 workbook 基本结构
- 展示 `workbook_context`
- 展示 `excel_plan`
- 确认后生成新文件
- 下载生成结果
- 持久化任务 JSON 以支持刷新后查询

## 当前不支持的能力

- `.xls`
- VBA / 宏
- 数据透视表
- Office 插件
- 直接控制本地 Excel 软件
- 执行 LLM 生成的 Python 代码
- 登录注册
- 权限系统
- 云端部署

## 测试用例

### 验收场景 1

不上传文件，输入：

```text
帮我生成一份药店终端拜访记录表，包含拜访日期、门店名称、地区、拜访人、产品名称、客户反馈、跟进事项、跟进状态，并生成地区汇总页。
```

期望：

- 生成执行计划
- 用户确认后生成 xlsx
- xlsx 可以正常打开
- 包含拜访明细 sheet 和地区汇总 sheet

### 验收场景 2

上传销售明细 `.xlsx`，输入：

```text
根据这个表，按部门统计销售额合计、订单数和平均客单价，并生成一个汇总 sheet。
```

期望：

- 能读取上传文件 sheet 和表头
- 能生成执行计划
- 用户确认后生成新 xlsx
- 不覆盖原文件

### 验收场景 3

上传普通 `.xlsx`，输入：

```text
帮我把这个表格整理得正式一点，表头加粗，自动列宽，冻结首行，增加筛选。
```

期望：

- 生成格式化计划
- 输出新 xlsx
- 表头加粗
- 冻结首行
- 自动筛选
- 自动列宽
