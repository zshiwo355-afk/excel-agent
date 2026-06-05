<template>
  <div class="workspace">
    <TaskHistory
      :tasks="tasks"
      :active-task-id="activeTaskId"
      @select="selectTask"
      @delete="handleDeleteTask"
      @refresh="fetchTasks"
      @new-task="startNewTask"
    />

    <section class="conversation-panel">
      <div ref="conversationScrollRef" class="conversation-scroll">
        <div class="conversation-inner">
          <section class="workspace-hero" :class="{ 'is-empty': !activeTask && !showDraftMessage }">
            <div class="hero-copy">
              <div class="hero-kicker">{{ heroKicker }}</div>
              <h1 class="hero-title">{{ heroTitle }}</h1>
              <p class="hero-description">{{ heroDescription }}</p>
            </div>

            <div class="hero-stats">
              <div v-for="item in heroStats" :key="item.label" class="hero-stat">
                <span class="hero-stat-label">{{ item.label }}</span>
                <strong class="hero-stat-value">{{ item.value }}</strong>
              </div>
            </div>

            <div v-if="heroChips.length" class="hero-chips">
              <span v-for="chip in heroChips" :key="chip" class="hero-chip">
                {{ chip }}
              </span>
            </div>
          </section>

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

            <AgentMessage
              v-if="isThinkingPhase"
              title="思考中"
              status="planning"
              :time="formatTime(activeTask.updated_at)"
            >
              <p class="agent-copy">{{ thinkingStatusText }}</p>
            </AgentMessage>

            <AgentMessage v-else title="任务已接收" :status="intakeStatus" :time="formatTime(activeTask.updated_at)">
              <p class="agent-copy">
                已收到任务{{ uploadedFileNames.length ? `，共上传 ${uploadedFileNames.length} 个文件` : "。" }}
              </p>
            </AgentMessage>

            <AgentMessage
              v-if="!isThinkingPhase && activeTask.workbook_contexts?.length"
              title="表格结构分析"
              :status="analysisStatus"
            >
              <div class="analysis-list">
                <div>已分析工作簿：{{ activeTask.workbook_contexts.length }}</div>
                <div v-for="context in activeTask.workbook_contexts" :key="context.file_id || context.file_name">
                  {{ context.file_name }}：{{ context.sheet_names?.join("、") || "未识别" }}
                </div>
              </div>
            </AgentMessage>

            <AgentMessage
              v-if="!isThinkingPhase && activeTask.excel_plan"
              title="Agent 计划"
              :status="planStatus"
            >
              <PlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage
              v-if="!isThinkingPhase && activeTask.task_plan"
              title="任务拆解"
              :status="taskPlanStatus"
            >
              <TaskPlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage
              v-if="!isThinkingPhase && timelineVisible"
              title="执行进度"
              :status="activeTask.status"
            >
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

          <section v-else class="welcome-panel">
            <div class="welcome-copy">
              <div class="welcome-title">开始一个新的 Excel 任务</div>
              <p>输入需求并上传 `.xlsx`，Agent 会先生成可确认的执行计划，再输出结果文件。</p>
            </div>
            <div class="welcome-grid">
              <div class="welcome-item">
                <strong>排序整理</strong>
                <span>按字段排序、删除空行、统一表头格式</span>
              </div>
              <div class="welcome-item">
                <strong>批量合并</strong>
                <span>多工作簿映射字段后汇总为总表</span>
              </div>
              <div class="welcome-item">
                <strong>结构拆分</strong>
                <span>按列值拆分 sheet，生成独立结果</span>
              </div>
            </div>
          </section>
        </div>
      </div>

      <ChatPanel
        :message="message"
        :files="uploadFiles"
        :loading="creating"
        :placeholder="composerPlaceholder"
        :submit-label="composerSubmitLabel"
        @update:message="message = $event"
        @file-change="handleFileChange"
        @submit="handlePrimarySubmit"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import AgentMessage from "../components/AgentMessage.vue";
import ChatPanel from "../components/ChatPanel.vue";
import DebugDetails from "../components/DebugDetails.vue";
import PlanPanel from "../components/PlanPanel.vue";
import ResultPanel from "../components/ResultPanel.vue";
import TaskHistory from "../components/TaskHistory.vue";
import TaskPlanPanel from "../components/TaskPlanPanel.vue";
import TaskTimeline from "../components/TaskTimeline.vue";
import { confirmTask, createTask, deleteTask, getDownloadUrl, getTask, listTasks } from "../api/taskApi";

const tasks = ref([]);
const activeTaskId = ref("");
const message = ref("");
const uploadFiles = ref([]);
const creating = ref(false);
const confirming = ref(false);
const draftRequest = ref(null);
const pollingTimer = ref(null);
const conversationScrollRef = ref(null);

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
const intakeStatus = computed(() => activeTask.value ? "completed" : "");
const analysisStatus = computed(() => activeTask.value?.workbook_contexts?.length ? "completed" : "");
const planStatus = computed(() => activeTask.value?.excel_plan ? "completed" : "");
const taskPlanStatus = computed(() => activeTask.value?.task_plan ? "completed" : "");
const showDraftMessage = computed(() => creating.value && draftRequest.value);
const nowLabel = computed(() => new Date().toLocaleString());
const isThinkingPhase = computed(() => activeTask.value?.status === "planning");
const thinkingStatusText = computed(() => activeTask.value?.status_message || "正在思考");
const composerPlaceholder = computed(() => "描述你想让 Excel Agent 执行的任务，支持一次上传一个或多个 .xlsx 文件。");
const composerSubmitLabel = computed(() => "发送");
const timelineVisible = computed(() => {
  const logs = activeTask.value?.execution_logs || activeTask.value?.logs || [];
  return Boolean(logs.length || activeTask.value?.status);
});
const currentFileNames = computed(() => {
  if (showDraftMessage.value) {
    return draftRequest.value?.fileNames || [];
  }
  return uploadedFileNames.value;
});
const currentStatusLabel = computed(() => {
  if (showDraftMessage.value) return "创建中";
  return statusLabel(activeTask.value?.status);
});
const heroKicker = computed(() => {
  if (showDraftMessage.value) return "Task Intake";
  if (activeTask.value) return "Active Workbook Flow";
  return "Excel Workflow Console";
});
const heroTitle = computed(() => {
  if (showDraftMessage.value) return "正在创建新任务";
  if (activeTask.value?.message) return activeTask.value.message;
  return "把排序、清洗、合并交给 Agent";
});
const heroDescription = computed(() => {
  if (showDraftMessage.value) {
    return "请求已提交，正在创建任务并准备分析上传的工作簿。";
  }
  if (activeTask.value) {
    const updatedAt = formatTime(activeTask.value.updated_at);
    return `${currentStatusLabel.value}${updatedAt ? `，最近更新于 ${updatedAt}` : ""}。`;
  }
  return "侧栏保留历史记录，主线程只展示当前任务的上下文、计划、进度和结果。";
});
const heroStats = computed(() => {
  if (showDraftMessage.value || activeTask.value) {
    return [
      { label: "当前状态", value: currentStatusLabel.value },
      { label: "关联文件", value: currentFileNames.value.length || 0 },
      {
        label: "计划节点",
        value: activeTask.value?.task_plan?.steps?.length
          || activeTask.value?.excel_plan?.sheets?.length
          || 0,
      },
    ];
  }

  return [
    { label: "历史任务", value: tasks.value.length },
    { label: "已完成", value: tasks.value.filter((item) => item.status === "completed").length },
    {
      label: "进行中",
      value: tasks.value.filter((item) => ["planning", "running"].includes(item.status)).length,
    },
  ];
});
const heroChips = computed(() => {
  if (currentFileNames.value.length) {
    return currentFileNames.value.slice(0, 4);
  }
  return ["排序", "格式化", "合并总表", "按列拆分"];
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
    if (activeTaskId.value && !tasks.value.some((item) => item.task_id === activeTaskId.value)) {
      activeTaskId.value = tasks.value[0]?.task_id || "";
    } else if (!activeTaskId.value && tasks.value.length) {
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

const stopPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value);
    pollingTimer.value = null;
  }
};

const ensurePolling = () => {
  stopPolling();
  if (!activeTaskId.value) return;
  if (!["planning", "running"].includes(activeTask.value?.status || "")) return;
  pollingTimer.value = setInterval(() => {
    refreshTask(activeTaskId.value).catch(() => {});
  }, 500);
};

const handlePrimarySubmit = async () => {
  await handleCreateTask();
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
    activeTaskId.value = task.task_id;
    const index = tasks.value.findIndex((item) => item.task_id === task.task_id);
    if (index >= 0) {
      tasks.value[index] = task;
    } else {
      tasks.value.unshift(task);
    }
    ensurePolling();
    await refreshTask(task.task_id);
    await fetchTasks();
    message.value = "";
    uploadFiles.value = [];
    draftRequest.value = null;
    if (task.status === "failed") {
      ElMessage.error("任务创建失败");
    } else {
      ElMessage.success("任务已开始思考");
    }
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
    const index = tasks.value.findIndex((item) => item.task_id === activeTaskId.value);
    if (index >= 0) {
      tasks.value[index] = { ...tasks.value[index], status: "running" };
    }
    ensurePolling();
    const task = await confirmTask(activeTaskId.value);
    const refreshedIndex = tasks.value.findIndex((item) => item.task_id === activeTaskId.value);
    if (refreshedIndex >= 0) {
      tasks.value[refreshedIndex] = task;
    }
    await refreshTask(activeTaskId.value);
    ElMessage.success("任务已开始执行");
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

const handleDeleteTask = async (taskIds) => {
  const ids = Array.isArray(taskIds) ? taskIds : [taskIds];
  const deletingTasks = tasks.value.filter((item) => ids.includes(item.task_id));
  if (!deletingTasks.length) return;
  const isBatchDelete = deletingTasks.length > 1;

  try {
    await ElMessageBox.confirm(
      isBatchDelete
        ? `删除后会同时移除这 ${deletingTasks.length} 条历史记录及其上传文件、生成结果，且不可恢复。`
        : "删除后会同时移除该任务的历史记录、上传文件和生成结果，且不可恢复。",
      "删除历史任务",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );
  } catch {
    return;
  }

  try {
    if (ids.includes(activeTaskId.value)) {
      stopPolling();
    }
    await Promise.all(ids.map((id) => deleteTask(id)));
    tasks.value = tasks.value.filter((item) => !ids.includes(item.task_id));
    if (ids.includes(activeTaskId.value)) {
      activeTaskId.value = tasks.value[0]?.task_id || "";
    }
    if (activeTaskId.value) {
      await refreshTask(activeTaskId.value);
    }
    ElMessage.success(isBatchDelete ? "历史任务组已删除" : "历史任务已删除");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "删除任务失败");
  }
};

const startNewTask = () => {
  stopPolling();
  activeTaskId.value = "";
  message.value = "";
  uploadFiles.value = [];
  draftRequest.value = null;
};

const formatTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};

const statusLabel = (status) => {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "needs_input") return "待补充";
  if (status === "waiting_confirm") return "待确认";
  if (status === "waiting_step_confirm") return "待步骤确认";
  if (status === "running") return "执行中";
  if (status === "planning") return "规划中";
  return "待开始";
};

const scrollConversationToBottom = (behavior = "smooth") => {
  const container = conversationScrollRef.value;
  if (!container) return;
  container.scrollTo({
    top: container.scrollHeight,
    behavior,
  });
};

const followConversation = (behavior = "smooth") => {
  nextTick(() => scrollConversationToBottom(behavior));
};

onMounted(fetchTasks);

watch(activeTask, () => {
  ensurePolling();
}, { deep: true });

watch(
  () => [activeTaskId.value, showDraftMessage.value],
  () => {
    followConversation("auto");
  },
);

watch(
  () => [
    activeTask.value?.status || "",
    activeTask.value?.status_message || "",
    activeTask.value?.updated_at || "",
    activeTask.value?.logs?.length || 0,
    activeTask.value?.execution_steps?.length || 0,
    activeTask.value?.current_step_index || 0,
    activeTask.value?.output_file_path || "",
  ],
  () => {
    if (showDraftMessage.value || ["planning", "running"].includes(activeTask.value?.status || "")) {
      followConversation("smooth");
    }
  },
);

onBeforeUnmount(() => {
  stopPolling();
});
</script>
