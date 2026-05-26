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
      <div
        v-for="group in groupedTasks"
        :key="group.key"
        class="history-group"
        :class="{ active: group.tasks.some((item) => item.task_id === activeTaskId) }"
      >
        <div class="history-entry group-entry" @click="selectGroup(group)">
          <div class="entry-topline">
            <div class="entry-title">{{ group.title }}</div>
            <div class="entry-count" v-if="group.tasks.length > 1">{{ group.tasks.length }}</div>
          </div>
          <div class="entry-meta">
            <el-tag size="small" effect="plain" :type="statusType(group.latest.status)">
              {{ group.latest.status }}
            </el-tag>
            <span>{{ formatTime(group.latest.updated_at) }}</span>
          </div>
          <div v-if="group.fileName" class="entry-file">{{ group.fileName }}</div>
        </div>

        <div v-if="isExpanded(group)" class="subtask-list">
          <button
            v-for="item in group.tasks"
            :key="item.task_id"
            type="button"
            class="subtask-entry"
            :class="{ active: item.task_id === activeTaskId }"
            @click="$emit('select', item.task_id)"
          >
            <div class="subtask-title">{{ subtaskTitle(item, group) }}</div>
            <div class="subtask-meta">
              <el-tag size="small" effect="plain" :type="statusType(item.status)">
                {{ item.status }}
              </el-tag>
              <span>{{ formatTime(item.updated_at) }}</span>
            </div>
          </button>
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

const statusType = (status) => {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "waiting_confirm") return "warning";
  return "info";
};

const shortTitle = (message) => {
  if (!message) return "未命名任务";
  return message.length > 20 ? `${message.slice(0, 20)}...` : message;
};

const formatTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};

const uploadedName = (task) => task?.uploaded_file_path?.split("/").pop() || "";

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
    return text.length > 18 ? `${text.slice(0, 18)}...` : text;
  }
  return formatTime(task.created_at);
};
</script>
