# Excel Agent Studio Frontend

## 项目介绍

前端使用 Vue3 + Vite + Element Plus，提供三栏式本地 Web 页面：

- 左侧：任务历史
- 中间：自然语言输入与 `.xlsx` 上传
- 右侧：执行计划、文件分析、执行结果与日志

## 前端启动方式

```bash
cd frontend
npm install
npm run dev
```

默认访问地址通常为 `http://127.0.0.1:5173`。

## MVP 支持能力

- 输入自然语言需求
- 上传 `.xlsx`
- 调用后端生成执行计划
- 查看 `workbook_context`
- 查看 `excel_plan`
- 确认执行任务
- 下载输出的 `.xlsx`
- 查看错误信息和执行日志
