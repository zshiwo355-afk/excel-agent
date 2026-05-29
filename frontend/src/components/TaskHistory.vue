<template>
  <aside class="history-shell">
    <div class="history-top">
      <div>
        <div class="history-brand">Excel Agent Studio</div>
        <div class="history-sub">本地表格 Agent</div>
      </div>
      <el-button type="primary" plain @click="$emit('new-task')">新建任务</el-button>
    </div>

    <div class="history-actions">
      <el-button text @click="$emit('refresh')">刷新</el-button>
    </div>

    <el-scrollbar height="calc(100vh - 180px)">
      <div class="history-list">
      <div
        v-for="group in groupedTasks"
        :key="group.key"
        class="history-group"
      >
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

        <div v-if="isExpanded(group)" class="subtask-list">
          <button
            v-for="item in group.tasks"
            :key="item.task_id"
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
        </div>
      </div>
      </div>
      <el-empty v-if="!groupedTasks.length" description="暂无历史任务" />
    </el-scrollbar>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from "vue";

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

const emit = defineEmits(["select", "refresh", "new-task"]);

const expandedKeys = ref(new Set());

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
  if (status === "waiting_confirm" || status === "waiting_step_confirm") return "is-pending";
  return "is-neutral";
};

const statusLabel = (status) => {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
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
.history-list {
  display: grid;
  gap: 14px;
  padding-right: 4px;
}

.history-group {
  display: grid;
  gap: 10px;
}

.history-entry {
  width: 100%;
  padding: 14px 14px 13px;
  border: 1px solid #d9e2ec;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.history-entry:hover {
  border-color: #bfd0e3;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.history-entry.selected {
  border-color: #7aa2d6;
  box-shadow: 0 16px 30px rgba(64, 112, 173, 0.14);
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
  color: #2f7d32;
  background: #eef9ef;
  border-color: #b9e0bc;
}

.status-pill.is-failed {
  color: #c2410c;
  background: #fff1eb;
  border-color: #f7bea8;
}

.status-pill.is-pending {
  color: #9a6700;
  background: #fff7db;
  border-color: #f3d98a;
}

.status-pill.is-neutral {
  color: #475569;
  background: #f1f5f9;
  border-color: #dbe4ee;
}

.entry-time {
  color: #7b8794;
  font-size: 12px;
  white-space: nowrap;
}

.entry-title {
  display: -webkit-box;
  overflow: hidden;
  color: #16202a;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.entry-file {
  margin-top: 10px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.entry-summary {
  margin-top: 10px;
  color: #7b8794;
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
  background: linear-gradient(180deg, #d7e2ee 0%, #e7edf4 100%);
}

.subtask-entry {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 8px 0 8px 2px;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.subtask-dot {
  width: 9px;
  height: 9px;
  margin-top: 6px;
  border-radius: 999px;
  background: #94a3b8;
  box-shadow: 0 0 0 4px #f8fafc;
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
  color: #334155;
  font-size: 13px;
  line-height: 1.45;
  word-break: break-word;
}

.subtask-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8a94a6;
  font-size: 12px;
  flex-wrap: wrap;
}

.subtask-status {
  color: #526071;
}

.subtask-entry.active .subtask-title {
  color: #0f172a;
  font-weight: 600;
}

.subtask-entry.active .subtask-meta {
  color: #64748b;
}
</style>
