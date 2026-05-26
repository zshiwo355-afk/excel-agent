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
  { keyword: "Upload saved to", label: "上传文件" },
  { keyword: "File analysis completed.", label: "分析文件" },
  { keyword: "Detected sheets:", label: "识别 sheet" },
  { keyword: "Detected header row:", label: "识别表头行" },
  { keyword: "Detected data start row:", label: "识别数据起始行" },
  { keyword: "Calling planner model", label: "生成执行计划" },
  { keyword: "ExcelPlan validation passed.", label: "计划校验通过" },
  { keyword: "Executing ExcelPlan.", label: "执行 ExcelPlan" },
  { keyword: "Applying style to sheet:", label: "正在应用格式化" },
  { keyword: "Sorting sheet", label: "正在排序" },
  { keyword: "Sort completed", label: "排序完成" },
  { keyword: "Workbook validation completed", label: "输出校验完成" },
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
      detail: pattern.keyword === "Detected sheets:" || pattern.keyword === "Sorting sheet" ? log : "",
    });
  });

  if (!matched.length && props.task?.status === "planning") {
    matched.push({ label: "正在创建任务", detail: "" });
  }
  return matched;
});
</script>
