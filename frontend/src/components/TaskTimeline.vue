<template>
  <div class="timeline-list">
    <div v-for="(step, index) in steps" :key="`${index}-${step.label}`" class="timeline-item">
      <span class="timeline-icon" :class="statusClass(step.status)">{{ statusIcon(step.status) }}</span>
      <div>
        <div class="timeline-label">
          <span class="timeline-phase">{{ phaseLabel(step.phase) }}</span>
          {{ step.label }}
        </div>
        <div v-if="step.detail" class="timeline-detail">{{ step.detail }}</div>
        <div v-if="step.resultSummary" class="timeline-detail">{{ step.resultSummary }}</div>
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
const executionSteps = computed(() => props.task?.execution_steps || []);

const patterns = [
  { keyword: "Task created.", label: "Create task", phase: "planning" },
  { keyword: "Upload saved:", label: "Save upload", phase: "planning" },
  { keyword: "File analysis started.", label: "Analyze workbook", phase: "planning" },
  { keyword: "Detected sheets in", label: "Inspect sheets", phase: "planning" },
  { keyword: "Calling planner model", label: "Build plan", phase: "planning" },
  { keyword: "ExcelPlan validation passed.", label: "Validate plan", phase: "planning" },
  { keyword: "Executing step", label: "Execute step", phase: "execution" },
  { keyword: "Step validation:", label: "Validate step", phase: "execution" },
  { keyword: "Executing merge_workbooks.", label: "Merge workbooks", phase: "execution" },
  { keyword: "Executing ExcelPlan.", label: "Run ExcelPlan", phase: "execution" },
  { keyword: "Workbook written to", label: "Write output file", phase: "execution" },
];

const steps = computed(() => {
  if (executionSteps.value.length) {
    return executionSteps.value.map((step) => ({
      label: step.title,
      detail: step.detail,
      status: step.status,
      phase: step.phase || "execution",
      resultSummary: step.result_summary,
    }));
  }

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
      status: "completed",
      phase: pattern.phase,
      resultSummary: "",
    });
  });

  if (!matched.length && props.task?.status === "planning") {
    matched.push({
      label: "Prepare task",
      detail: props.task?.status_message || "",
      status: "running",
      phase: "planning",
      resultSummary: "",
    });
  }

  return matched;
});

const statusClass = (status) => {
  if (status === "running") return "is-running";
  if (status === "failed") return "is-failed";
  if (status === "pending") return "is-pending";
  return "is-completed";
};

const statusIcon = (status) => {
  if (status === "running") return "...";
  if (status === "failed") return "!";
  if (status === "pending") return "-";
  return "OK";
};

const phaseLabel = (phase) => {
  if (phase === "planning") return "Plan";
  return "Run";
};
</script>
