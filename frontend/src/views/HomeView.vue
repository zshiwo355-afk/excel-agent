<template>
  <div class="workspace">
    <TaskHistory
      :tasks="tasks"
      :active-task-id="activeTaskId"
      @select="selectTask"
      @refresh="fetchTasks"
      @new-task="startNewTask"
    />

    <section class="conversation-panel">
      <div class="conversation-scroll">
        <div class="conversation-inner">
          <template v-if="showDraftMessage">
            <AgentMessage role="user" :time="nowLabel">
              <div class="user-copy">{{ draftRequest.message }}</div>
              <div v-if="draftRequest.fileNames.length" class="user-file">
                已选择 {{ draftRequest.fileNames.length }} 个文件：{{ draftRequest.fileNames.join("、") }}
              </div>
            </AgentMessage>
            <AgentMessage title="正在创建任务" status="planning">
              <p class="agent-copy">已收到任务，正在创建并准备分析表格。</p>
            </AgentMessage>
          </template>

          <template v-else-if="activeTask">
            <AgentMessage role="user" :time="formatTime(activeTask.created_at)">
              <div class="user-copy">{{ activeTask.message }}</div>
              <div v-if="uploadedFileNames.length" class="user-file">
                已选择 {{ uploadedFileNames.length }} 个文件：{{ uploadedFileNames.join("、") }}
              </div>
            </AgentMessage>

            <AgentMessage title="任务已接收" :status="activeTask.status" :time="formatTime(activeTask.updated_at)">
              <p class="agent-copy">
                已收到任务{{ uploadedFileNames.length ? `，共上传 ${uploadedFileNames.length} 个文件` : "。" }}
              </p>
            </AgentMessage>

            <AgentMessage v-if="activeTask.workbook_contexts?.length" title="表格结构分析" :status="activeTask.status">
              <div class="analysis-list">
                <div>已分析工作簿：{{ activeTask.workbook_contexts.length }}</div>
                <div v-for="context in activeTask.workbook_contexts" :key="context.file_id || context.file_name">
                  {{ context.file_name }}：{{ context.sheet_names?.join("、") || "未识别" }}
                </div>
              </div>
            </AgentMessage>

            <AgentMessage v-if="activeTask.excel_plan" title="Agent 计划" :status="activeTask.status">
              <PlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage v-if="activeTask.task_plan" title="任务拆解" :status="activeTask.status">
              <TaskPlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage v-if="timelineVisible" title="执行进度" :status="activeTask.status">
              <TaskTimeline :task="activeTask" />
              <DebugDetails :sections="debugSections" />
            </AgentMessage>

            <AgentMessage
              v-if="activeTask.status === 'completed' || activeTask.status === 'failed'"
              :title="activeTask.status === 'completed' ? '执行结果' : '错误信息'"
              :status="activeTask.status"
            >
              <ResultPanel :task="activeTask" :download-url="downloadUrl" />
            </AgentMessage>
          </template>

          <div v-else class="welcome-card">
            <div class="welcome-title">开始一个新的 Excel 任务</div>
            <p>在下方输入需求，上传一个或多个 `.xlsx`，让 Agent 修改、排序、格式化或合并成总表。</p>
          </div>
        </div>
      </div>

      <ChatPanel
        :message="message"
        :file-names="uploadFileNames"
        :loading="creating"
        @update:message="message = $event"
        @file-change="handleFileChange"
        @submit="handleCreateTask"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import AgentMessage from "../components/AgentMessage.vue";
import ChatPanel from "../components/ChatPanel.vue";
import DebugDetails from "../components/DebugDetails.vue";
import PlanPanel from "../components/PlanPanel.vue";
import ResultPanel from "../components/ResultPanel.vue";
import TaskHistory from "../components/TaskHistory.vue";
import TaskPlanPanel from "../components/TaskPlanPanel.vue";
import TaskTimeline from "../components/TaskTimeline.vue";
import { confirmTask, createTask, getDownloadUrl, getTask, listTasks } from "../api/taskApi";

const tasks = ref([]);
const activeTaskId = ref("");
const message = ref("");
const uploadFiles = ref([]);
const creating = ref(false);
const confirming = ref(false);
const draftRequest = ref(null);

const activeTask = computed(
  () => tasks.value.find((item) => item.task_id === activeTaskId.value) || null,
);

const uploadFileNames = computed(() => uploadFiles.value.map((item) => item.name).filter(Boolean));
const uploadedFileNames = computed(() => {
  if (activeTask.value?.uploaded_files?.length) {
    return activeTask.value.uploaded_files.map((item) => item.file_name);
  }
  if (activeTask.value?.uploaded_file_path) {
    return [activeTask.value.uploaded_file_path.split("/").pop()];
  }
  return [];
});
const downloadUrl = computed(() =>
  activeTaskId.value ? getDownloadUrl(activeTaskId.value) : "",
);
const showDraftMessage = computed(() => creating.value && draftRequest.value);
const nowLabel = computed(() => new Date().toLocaleString());
const timelineVisible = computed(() => {
  const logs = activeTask.value?.execution_logs || activeTask.value?.logs || [];
  return Boolean(logs.length || activeTask.value?.status);
});

const debugSections = computed(() => [
  {
    title: "查看执行日志",
    content: activeTask.value?.execution_logs || activeTask.value?.logs || [],
  },
  {
    title: "查看 Workbook 分析",
    content: activeTask.value?.workbook_contexts?.length
      ? activeTask.value?.workbook_contexts
      : activeTask.value?.workbook_context || null,
  },
  {
    title: "查看 TaskPlan JSON",
    content: activeTask.value?.task_plan || null,
  },
  {
    title: "查看 ExcelPlan JSON",
    content: activeTask.value?.excel_plan || null,
  },
  {
    title: "查看原始 LLM 输出",
    content: activeTask.value?.raw_llm_response || null,
  },
  {
    title: "查看技术错误",
    content: activeTask.value?.technical_error || null,
  },
]);

const fetchTasks = async () => {
  try {
    tasks.value = await listTasks();
    if (!activeTaskId.value && tasks.value.length) {
      activeTaskId.value = tasks.value[0].task_id;
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取任务列表失败");
  }
};

const refreshTask = async (taskId) => {
  const task = await getTask(taskId);
  const index = tasks.value.findIndex((item) => item.task_id === taskId);
  if (index >= 0) {
    tasks.value[index] = task;
  } else {
    tasks.value.unshift(task);
  }
  activeTaskId.value = taskId;
};

const handleCreateTask = async () => {
  const trimmed = message.value.trim();
  if (!trimmed) {
    ElMessage.warning("请输入你的 Excel 需求");
    return;
  }
  creating.value = true;
  draftRequest.value = {
    message: trimmed,
    fileNames: uploadFileNames.value,
  };
  try {
    const task = await createTask({
      message: trimmed,
      file: uploadFiles.value[0] || null,
      files: uploadFiles.value,
    });
    await fetchTasks();
    activeTaskId.value = task.task_id;
    await refreshTask(task.task_id);
    message.value = "";
    uploadFiles.value = [];
    draftRequest.value = null;
    ElMessage.success(task.status === "failed" ? "任务创建失败" : "执行计划已生成");
  } catch (error) {
    draftRequest.value = null;
    ElMessage.error(error.response?.data?.detail || "创建任务失败");
  } finally {
    creating.value = false;
  }
};

const handleConfirmTask = async () => {
  if (!activeTaskId.value) return;
  confirming.value = true;
  try {
    await confirmTask(activeTaskId.value);
    await refreshTask(activeTaskId.value);
    ElMessage.success("Excel 已生成");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "确认任务失败");
  } finally {
    confirming.value = false;
  }
};

const handleFileChange = (files) => {
  uploadFiles.value = files || [];
};

const selectTask = async (taskId) => {
  await refreshTask(taskId);
};

const startNewTask = () => {
  activeTaskId.value = "";
  message.value = "";
  uploadFiles.value = [];
  draftRequest.value = null;
};

const formatTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};

onMounted(fetchTasks);
</script>
