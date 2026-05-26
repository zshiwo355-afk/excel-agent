<template>
  <div class="message-row" :class="`role-${role}`">
    <div class="message-shell">
      <div v-if="role === 'agent'" class="message-label">Agent</div>
      <div class="message-card">
        <div v-if="title || status || time" class="message-head">
          <div class="message-title-wrap">
            <div v-if="title" class="message-title">{{ title }}</div>
            <el-tag v-if="status" size="small" :type="statusType">{{ status }}</el-tag>
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
  if (props.status === "waiting_confirm" || props.status === "waiting_step_confirm") return "warning";
  return "info";
});
</script>
