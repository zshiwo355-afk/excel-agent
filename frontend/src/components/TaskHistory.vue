<template>
  <aside class="history-shell">
    <div class="history-top">
      <div class="history-brand-block">
        <div class="history-brand">Excel Agent Studio</div>
        <div class="history-sub">面向表格处理的本地工作台</div>
      </div>
      <el-button class="history-button" type="primary" @click="$emit('new-task')">
        <el-icon><Plus /></el-icon>
        <span>新任务</span>
      </el-button>
    </div>

    <div class="history-metrics">
      <div class="history-metric">
        <span class="metric-label">总任务</span>
        <strong class="metric-value">{{ tasks.length }}</strong>
      </div>
      <div class="history-metric">
        <span class="metric-label">已完成</span>
        <strong class="metric-value">{{ completedCount }}</strong>
      </div>
      <div class="history-metric">
        <span class="metric-label">进行中</span>
        <strong class="metric-value">{{ runningCount }}</strong>
      </div>
    </div>

    <div class="history-actions">
      <el-button class="history-refresh" text @click="$emit('refresh')">
        <el-icon><RefreshRight /></el-icon>
        <span>刷新列表</span>
      </el-button>
    </div>

    <el-scrollbar class="history-scroll">
      <div class="history-list">
      <div
        v-for="group in groupedTasks"
        :key="group.key"
        class="history-group"
      >
        <div class="history-entry-shell">
          <button
            type="button"
            class="history-entry group-entry"
            :class="{ selected: group.tasks.some((item) => item.task_id === activeTaskId) }"
            @click="selectGroup(group)"
          >
            <div class="entry-head">
              <span class="status-pill" :class="statusClass(group.latest.status)">
                {{ statusLabel(group.latest.status) }}
              </span>
              <span class="entry-time">{{ formatTime(group.latest.updated_at) }}</span>
            </div>

            <div class="entry-title">{{ group.title }}</div>

            <div v-if="group.fileName" class="entry-file">
              {{ group.fileName }}
            </div>

            <div v-if="group.tasks.length > 1" class="entry-summary">
              共 {{ group.tasks.length }} 条相关记录
            </div>
          </button>

          <button
            type="button"
            class="entry-delete"
            :aria-label="`删除${group.title}`"
            @click.stop="$emit('delete', group.tasks.map((item) => item.task_id))"
          >
            <el-icon><Delete /></el-icon>
          </button>
        </div>

        <div v-if="isExpanded(group)" class="subtask-list">
          <div
            v-for="item in group.tasks"
            :key="item.task_id"
            class="subtask-row"
          >
            <button
              type="button"
              class="subtask-entry"
              :class="{ active: item.task_id === activeTaskId }"
              @click="$emit('select', item.task_id)"
            >
              <span class="subtask-dot" :class="statusClass(item.status)"></span>
              <div class="subtask-body">
                <div class="subtask-title">{{ subtaskTitle(item, group) }}</div>
                <div class="subtask-meta">
                  <span class="subtask-status">{{ statusLabel(item.status) }}</span>
                  <span>{{ formatTime(item.updated_at) }}</span>
                </div>
              </div>
            </button>
            <button
              type="button"
              class="subtask-delete"
              :aria-label="`删除${subtaskTitle(item, group)}`"
              @click.stop="$emit('delete', item.task_id)"
            >
              <el-icon><Delete /></el-icon>
            </button>
          </div>
        </div>
      </div>
      </div>
      <el-empty v-if="!groupedTasks.length" description="暂无历史任务" />
    </el-scrollbar>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Delete, Plus, RefreshRight } from "@element-plus/icons-vue";

const props = defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
  activeTaskId: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["select", "delete", "refresh", "new-task"]);

const expandedKeys = ref(new Set());
const completedCount = computed(() => props.tasks.filter((item) => item.status === "completed").length);
const runningCount = computed(() =>
  props.tasks.filter((item) => ["planning", "running", "waiting_confirm", "waiting_step_confirm"].includes(item.status)).length,
);

watch(
  () => props.activeTaskId,
  (taskId) => {
    if (!taskId) return;
    const group = groupedTasks.value.find((item) =>
      item.tasks.some((task) => task.task_id === taskId),
    );
    if (!group) return;
    expandedKeys.value = new Set([...expandedKeys.value, group.key]);
  },
  { immediate: true },
);

const statusClass = (status) => {
  if (status === "completed") return "is-success";
  if (status === "failed") return "is-failed";
  if (status === "needs_input" || status === "waiting_confirm" || status === "waiting_step_confirm") return "is-pending";
  return "is-neutral";
};

const statusLabel = (status) => {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "needs_input") return "待补充";
  if (status === "waiting_confirm") return "待确认";
  if (status === "waiting_step_confirm") return "待步骤确认";
  if (status === "running") return "执行中";
  if (status === "planning") return "规划中";
  return "处理中";
};

const shortTitle = (message) => {
  if (!message) return "未命名任务";
  return message.length > 24 ? `${message.slice(0, 24)}...` : message;
};

const formatTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};

const uploadedName = (task) => {
  if (task?.uploaded_files?.length) {
    return task.uploaded_files.map((item) => item.file_name).join("、");
  }
  return task?.uploaded_file_path?.split("/").pop() || "";
};

const normalizeMessage = (message) => {
  if (!message) return "未命名任务";
  return message
    .replace(/[，。、“”"'\s]/g, "")
    .replace(/从高到低|从低到高|升序|降序/g, "")
    .replace(/进行排序|排序|整理|正式一点/g, "")
    .slice(0, 18);
};

const groupKeyForTask = (task) => {
  const fileName = uploadedName(task);
  if (fileName) return `file:${fileName}`;
  return `msg:${normalizeMessage(task.message)}`;
};

const groupedTasks = computed(() => {
  const groups = [];
  const groupMap = new Map();

  props.tasks.forEach((task) => {
    const key = groupKeyForTask(task);
    if (!groupMap.has(key)) {
      const group = {
        key,
        title: shortTitle(task.message),
        fileName: uploadedName(task),
        latest: task,
        tasks: [],
      };
      groupMap.set(key, group);
      groups.push(group);
    }
    const group = groupMap.get(key);
    group.tasks.push(task);
    if (new Date(task.updated_at) > new Date(group.latest.updated_at)) {
      group.latest = task;
      group.title = shortTitle(task.message);
    }
  });

  return groups.map((group) => ({
    ...group,
    tasks: [...group.tasks].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    ),
  }));
});

const isExpanded = (group) => {
  if (group.tasks.length === 1) return false;
  if (group.tasks.some((item) => item.task_id === props.activeTaskId)) return true;
  return expandedKeys.value.has(group.key);
};

const selectGroup = (group) => {
  if (group.tasks.length > 1) {
    const next = new Set(expandedKeys.value);
    if (next.has(group.key)) {
      next.delete(group.key);
    } else {
      next.add(group.key);
    }
    expandedKeys.value = next;
  }
  emit("select", group.latest.task_id);
};

const subtaskTitle = (task, group) => {
  if (group.fileName) {
    const text = task.message || "执行记录";
    return text.length > 22 ? `${text.slice(0, 22)}...` : text;
  }
  return formatTime(task.created_at);
};
</script>

<style scoped>
.history-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 0;
}

.history-brand-block {
  min-width: 0;
}

.history-button {
  border-radius: 999px;
}

.history-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.history-metric {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.22);
}

.metric-label {
  color: rgba(226, 232, 240, 0.72);
  font-size: 11px;
}

.metric-value {
  color: #f8fafc;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}

.history-refresh {
  padding-left: 0;
}

.history-list {
  display: grid;
  gap: 14px;
  padding-right: 4px;
}

.history-scroll {
  flex: 1;
  min-height: 0;
}

.history-group {
  display: grid;
  gap: 10px;
}

.history-entry-shell {
  position: relative;
}

.history-entry {
  width: 100%;
  padding: 14px 50px 13px 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(21, 30, 45, 0.92) 0%, rgba(12, 20, 32, 0.92) 100%);
  box-shadow: 0 18px 36px rgba(2, 6, 23, 0.28);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.history-entry:hover {
  border-color: rgba(94, 234, 212, 0.36);
  box-shadow: 0 22px 42px rgba(15, 23, 42, 0.34);
  transform: translateY(-1px);
}

.history-entry.selected {
  border-color: rgba(94, 234, 212, 0.58);
  box-shadow: 0 24px 44px rgba(15, 23, 42, 0.42);
}

.entry-delete,
.subtask-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 999px;
  background: rgba(248, 113, 113, 0.12);
  color: rgba(253, 164, 175, 0.92);
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.entry-delete:hover,
.subtask-delete:hover {
  background: rgba(248, 113, 113, 0.2);
  color: #fecdd3;
  transform: translateY(-1px);
}

.entry-delete {
  position: absolute;
  top: 12px;
  right: 12px;
}

.entry-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-pill.is-success {
  color: #86efac;
  background: rgba(34, 197, 94, 0.16);
  border-color: rgba(34, 197, 94, 0.22);
}

.status-pill.is-failed {
  color: #fda4af;
  background: rgba(248, 113, 113, 0.16);
  border-color: rgba(248, 113, 113, 0.2);
}

.status-pill.is-pending {
  color: #fde68a;
  background: rgba(251, 191, 36, 0.16);
  border-color: rgba(251, 191, 36, 0.22);
}

.status-pill.is-neutral {
  color: #bae6fd;
  background: rgba(56, 189, 248, 0.14);
  border-color: rgba(56, 189, 248, 0.2);
}

.entry-time {
  color: rgba(203, 213, 225, 0.68);
  font-size: 12px;
  white-space: nowrap;
}

.entry-title {
  display: -webkit-box;
  overflow: hidden;
  color: #f8fafc;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.entry-file {
  margin-top: 10px;
  color: rgba(203, 213, 225, 0.76);
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.entry-summary {
  margin-top: 10px;
  color: rgba(148, 163, 184, 0.82);
  font-size: 12px;
}

.subtask-list {
  position: relative;
  display: grid;
  gap: 8px;
  margin-left: 14px;
  padding-left: 14px;
}

.subtask-list::before {
  content: "";
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 0;
  width: 1px;
  background: linear-gradient(180deg, rgba(94, 234, 212, 0.2) 0%, rgba(148, 163, 184, 0.08) 100%);
}

.subtask-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.subtask-entry {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  padding: 8px 0 8px 2px;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.subtask-delete {
  flex: 0 0 30px;
  margin-top: 2px;
}

.subtask-dot {
  width: 9px;
  height: 9px;
  margin-top: 6px;
  border-radius: 999px;
  background: #94a3b8;
  box-shadow: 0 0 0 4px rgba(15, 23, 42, 0.88);
  flex: 0 0 9px;
}

.subtask-dot.is-success {
  background: #6dbb73;
}

.subtask-dot.is-failed {
  background: #ef7d5b;
}

.subtask-dot.is-pending {
  background: #e7b93f;
}

.subtask-dot.is-neutral {
  background: #94a3b8;
}

.subtask-body {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.subtask-title {
  color: rgba(226, 232, 240, 0.9);
  font-size: 13px;
  line-height: 1.45;
  word-break: break-word;
}

.subtask-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(148, 163, 184, 0.82);
  font-size: 12px;
  flex-wrap: wrap;
}

.subtask-status {
  color: rgba(226, 232, 240, 0.7);
}

.subtask-entry.active .subtask-title {
  color: #ffffff;
  font-weight: 600;
}

.subtask-entry.active .subtask-meta {
  color: rgba(226, 232, 240, 0.74);
}
</style>
