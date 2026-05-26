<template>
  <div class="timeline-list">
    <div v-for="(step, index) in steps" :key="`${index}-${step.label}`" class="timeline-item">
      <span class="timeline-icon">✓</span>
      <div>
        <div class="timeline-label">{{ step.label }}</div>
        <div v-if="step.detail" class="timeline-detail">{{ step.detail }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  task: {
    type: Object,
    default: null,
  },
});

const logs = computed(() => props.task?.execution_logs || props.task?.logs || []);

const patterns = [
  { keyword: "Task created.", label: "创建任务" },
  { keyword: "Upload saved:", label: "上传文件" },
  { keyword: "File analysis started.", label: "开始分析文件" },
  { keyword: "Analyzing workbook:", label: "分析工作簿" },
  { keyword: "Detected sheets in", label: "识别 sheet" },
  { keyword: "File analysis completed.", label: "文件分析完成" },
  { keyword: "Calling planner model", label: "生成执行计划" },
  { keyword: "Calling planner model to generate TaskPlan.", label: "生成任务拆解" },
  { keyword: "ExcelPlan validation passed.", label: "计划校验通过" },
  { keyword: "Executing step", label: "执行步骤" },
  { keyword: "Step validation:", label: "步骤校验" },
  { keyword: "requires user confirmation", label: "等待步骤确认" },
  { keyword: "Executing merge_workbooks.", label: "执行合并" },
  { keyword: "Merging sheet", label: "合并来源 sheet" },
  { keyword: "Executing ExcelPlan.", label: "执行 ExcelPlan" },
  { keyword: "Sorting sheet", label: "正在排序" },
  { keyword: "Expected merged rows:", label: "预期合并行数" },
  { keyword: "Actual merged rows:", label: "实际合并行数" },
  { keyword: "Merge validation completed", label: "合并校验完成" },
  { keyword: "Workbook written to", label: "文件生成成功" },
];

const steps = computed(() => {
  const matched = [];
  const seen = new Set();

  logs.value.forEach((log) => {
    const pattern = patterns.find((item) => log.includes(item.keyword));
    if (!pattern) return;
    const key = `${pattern.label}-${log}`;
    if (seen.has(key)) return;
    seen.add(key);
    matched.push({
      label: pattern.label,
      detail: log,
    });
  });

  if (!matched.length && props.task?.status === "planning") {
    matched.push({ label: "正在创建任务", detail: "" });
  }
  return matched;
});
</script>
