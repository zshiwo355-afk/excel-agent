<template>
  <div class="message-row" :class="`role-${role}`">
    <div class="message-shell">
      <div class="message-label">{{ role === "agent" ? "Agent" : "用户" }}</div>
      <div class="message-card">
        <div v-if="title || status || time" class="message-head">
          <div class="message-title-wrap">
            <div v-if="title" class="message-title">{{ title }}</div>
            <el-tag v-if="status" size="small" :type="statusType" effect="plain">
              {{ statusLabel }}
            </el-tag>
          </div>
          <div v-if="time" class="message-time">{{ time }}</div>
        </div>
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  role: {
    type: String,
    default: "agent",
  },
  title: {
    type: String,
    default: "",
  },
  status: {
    type: String,
    default: "",
  },
  time: {
    type: String,
    default: "",
  },
});

const statusType = computed(() => {
  if (props.status === "completed") return "success";
  if (props.status === "failed") return "danger";
  if (props.status === "needs_input") return "warning";
  if (props.status === "waiting_confirm" || props.status === "waiting_step_confirm") return "warning";
  return "info";
});

const statusLabel = computed(() => {
  if (props.status === "completed") return "已完成";
  if (props.status === "failed") return "失败";
  if (props.status === "needs_input") return "待补充";
  if (props.status === "waiting_confirm") return "待确认";
  if (props.status === "waiting_step_confirm") return "待步骤确认";
  if (props.status === "planning") return "规划中";
  if (props.status === "running") return "执行中";
  return props.status;
});
</script>
