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
      <div
        ref="conversationScrollRef"
        class="conversation-scroll"
        @scroll="handleConversationScroll"
      >
        <div class="conversation-inner">
          <section v-if="activeTask || showDraftMessage" class="task-hero">
            <div class="task-hero-main">
              <div class="hero-kicker">Active Task</div>
              <h1 class="task-hero-title">
                {{ showDraftMessage ? "正在创建任务" : (activeTask?.message || "未命名任务") }}
              </h1>
              <p class="task-hero-description">{{ taskHeroDescription }}</p>
            </div>

            <div class="task-hero-side">
              <div class="task-hero-stats">
                <div class="task-hero-stat">
                  <span class="hero-stat-label">状态</span>
                  <strong class="hero-stat-value">{{ currentStatusLabel }}</strong>
                </div>
                <div class="task-hero-stat">
                  <span class="hero-stat-label">文件</span>
                  <strong class="hero-stat-value">{{ currentFileNames.length }}</strong>
                </div>
                <div class="task-hero-stat">
                  <span class="hero-stat-label">步骤</span>
                  <strong class="hero-stat-value">{{ timelineSteps.length }}</strong>
                </div>
              </div>

              <div class="task-hero-actions">
                <a
                  v-if="activeTask?.status === 'completed' && downloadUrl"
                  class="hero-download-link"
                  :href="downloadUrl"
                  target="_blank"
                >
                  下载结果
                </a>
              </div>
            </div>

            <div v-if="currentFileNames.length" class="hero-chips">
              <span v-for="fileName in currentFileNames" :key="fileName" class="hero-chip">
                {{ fileName }}
              </span>
            </div>
          </section>

          <section v-else class="workspace-hero is-empty">
            <div class="hero-copy">
              <div class="hero-kicker">Excel Workflow Console</div>
              <h1 class="hero-title">把分析、规划和执行放到同一个 Excel Agent 里</h1>
              <p class="hero-description">
                左侧保留历史任务，主区域像对话日志一样展示理解、规划、执行和结果，而不是只给一张最终总结卡片。
              </p>
            </div>

            <div class="hero-stats">
              <div class="hero-stat">
                <span class="hero-stat-label">历史任务</span>
                <strong class="hero-stat-value">{{ tasks.length }}</strong>
              </div>
              <div class="hero-stat">
                <span class="hero-stat-label">已完成</span>
                <strong class="hero-stat-value">{{ completedCount }}</strong>
              </div>
              <div class="hero-stat">
                <span class="hero-stat-label">进行中</span>
                <strong class="hero-stat-value">{{ runningCount }}</strong>
              </div>
            </div>
          </section>

          <template v-if="showDraftMessage">
            <AgentMessage role="user" :time="nowLabel">
              <div class="user-copy">{{ draftRequest.message }}</div>
              <div v-if="draftRequest.fileNames.length" class="user-file">
                已选择 {{ draftRequest.fileNames.length }} 个文件：{{ draftRequest.fileNames.join("、") }}
              </div>
            </AgentMessage>

            <AgentMessage title="创建任务" status="planning">
              <p class="agent-copy">请求已提交，正在保存文件并初始化任务。</p>
            </AgentMessage>
          </template>

          <template v-else-if="activeTask">
            <AgentMessage role="user" :time="formatTime(activeTask.created_at)">
              <div class="user-copy">{{ activeTask.message }}</div>
              <div v-if="uploadedFileNames.length" class="user-file">
                已上传 {{ uploadedFileNames.length }} 个文件：{{ uploadedFileNames.join("、") }}
              </div>
            </AgentMessage>

            <AgentMessage
              :title="primaryMessageTitle"
              :status="activeTask.status"
              :time="formatTime(activeTask.updated_at)"
            >
              <p class="agent-copy">{{ primaryMessageText }}</p>
            </AgentMessage>

            <template v-for="step in timelineSteps" :key="step.step_id">
              <AgentMessage
                :title="step.title"
                :status="stepStatus(step.status)"
                :time="stepTimeLabel(step)"
              >
                <div class="step-meta">
                  <span class="step-phase-badge">{{ phaseLabel(step.phase) }}</span>
                  <span class="step-status-copy">{{ stepStatusLabel(step.status) }}</span>
                </div>
                <p v-if="step.detail" class="agent-copy">{{ step.detail }}</p>
                <p v-if="step.result_summary" class="agent-copy step-result">{{ step.result_summary }}</p>
              </AgentMessage>
            </template>

            <AgentMessage
              v-if="activeTask.status === 'completed' || activeTask.status === 'failed'"
              :title="activeTask.status === 'completed' ? '执行结果' : '错误信息'"
              :status="activeTask.status"
            >
              <ResultPanel :task="activeTask" :download-url="downloadUrl" />
            </AgentMessage>

            <AgentMessage
              v-if="activeTask.excel_plan"
              title="执行计划"
              :status="planStatus"
            >
              <PlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage
              v-if="activeTask.task_plan"
              title="任务图"
              :status="taskPlanStatus"
            >
              <TaskPlanPanel
                :task="activeTask"
                :confirm-loading="confirming"
                @confirm="handleConfirmTask"
              />
            </AgentMessage>

            <AgentMessage v-if="hasDebugSections" title="调试详情">
              <DebugDetails :sections="debugSections" />
            </AgentMessage>
          </template>

          <section v-else class="welcome-panel">
            <div class="welcome-copy">
              <div class="welcome-title">开始一个新的 Excel 任务</div>
              <p>输入需求并上传一个或多个 `.xlsx` 文件，Agent 会逐步分析、规划并执行。</p>
            </div>
            <div class="welcome-grid">
              <div class="welcome-item">
                <strong>多表汇总</strong>
                <span>自动分析多个销售表并汇总为统一明细或统计表。</span>
              </div>
              <div class="welcome-item">
                <strong>结构化处理</strong>
                <span>支持排序、填充、拆分、清洗、插列等常见表格处理任务。</span>
              </div>
              <div class="welcome-item">
                <strong>过程可见</strong>
                <span>在页面里直接看到每一步状态变化，而不是只看最终结果。</span>
              </div>
            </div>
          </section>
        </div>
      </div>

      <button
        v-if="showJumpToLatest"
        type="button"
        class="jump-latest"
        @click="jumpToLatest"
      >
        回到底部
      </button>

      <ChatPanel
        :message="message"
        :files="uploadFiles"
        :loading="composerBusy"
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
const shouldAutoFollow = ref(true);

const activeTask = computed(
  () => tasks.value.find((item) => item.task_id === activeTaskId.value) || null,
);

const completedCount = computed(() => tasks.value.filter((item) => item.status === "completed").length);
const runningCount = computed(() =>
  tasks.value.filter((item) => ["planning", "running", "waiting_confirm", "waiting_step_confirm"].includes(item.status)).length,
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

const showDraftMessage = computed(() => creating.value && draftRequest.value);
const nowLabel = computed(() => new Date().toLocaleString());
const downloadUrl = computed(() => (
  activeTaskId.value ? getDownloadUrl(activeTaskId.value) : ""
));
const planStatus = computed(() => (activeTask.value?.excel_plan ? "completed" : ""));
const taskPlanStatus = computed(() => (activeTask.value?.task_plan ? "completed" : ""));
const composerPlaceholder = computed(() => "描述你想让 Excel Agent 执行的任务，支持一次上传一个或多个 .xlsx 文件。");
const composerBusy = computed(() => creating.value || ["planning", "running"].includes(activeTask.value?.status || ""));
const composerSubmitLabel = computed(() => {
  if (creating.value) return "创建中";
  if (activeTask.value?.status === "planning") return "思考中";
  if (activeTask.value?.status === "running") return "运行中";
  return "发送";
});

const timelineSteps = computed(() => activeTask.value?.execution_steps || []);

const debugSections = computed(() => ([
  {
    title: "查看执行日志",
    content: activeTask.value?.execution_logs || activeTask.value?.logs || [],
  },
  {
    title: "查看 Workbook 分析",
    content: activeTask.value?.workbook_contexts?.length
      ? activeTask.value.workbook_contexts
      : activeTask.value?.workbook_context || null,
  },
  {
    title: "查看目标理解",
    content: activeTask.value?.goal_understanding || null,
  },
  {
    title: "查看任务路由",
    content: activeTask.value?.task_route || null,
  },
  {
    title: "查看表格语义理解",
    content: activeTask.value?.workbook_semantics || null,
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
]));

const hasDebugSections = computed(() =>
  debugSections.value.some((section) => {
    if (section.content === null || section.content === undefined) return false;
    if (Array.isArray(section.content)) return section.content.length > 0;
    if (typeof section.content === "object") return Object.keys(section.content).length > 0;
    return String(section.content).trim().length > 0;
  }),
);

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

const taskHeroDescription = computed(() => {
  if (showDraftMessage.value) {
    return "请求已提交，正在准备文件分析和任务上下文。";
  }
  if (!activeTask.value) return "";
  const updatedAt = formatTime(activeTask.value.updated_at);
  const downloadHint = activeTask.value.status === "completed"
    ? " 已生成结果文件，可直接点击右侧“下载结果”。"
    : "";
  return `${currentStatusLabel.value}${updatedAt ? `，最近更新于 ${updatedAt}` : ""}。${downloadHint}`;
});

const primaryMessageTitle = computed(() => {
  if (!activeTask.value) return "";
  if (activeTask.value.status === "planning") return "Agent 正在思考";
  if (activeTask.value.status === "running") return "Agent 正在执行";
  if (activeTask.value.status === "completed") return "任务已完成";
  if (activeTask.value.status === "failed") return "任务执行失败";
  if (activeTask.value.status === "waiting_step_confirm") return "等待步骤确认";
  if (activeTask.value.status === "waiting_confirm") return "计划已生成";
  return "任务已接收";
});

const primaryMessageText = computed(() => {
  if (!activeTask.value) return "";
  if (activeTask.value.status === "planning") {
    return activeTask.value.status_message || "正在分析文件和生成计划。";
  }
  if (activeTask.value.status === "running") {
    return activeTask.value.status_message || "正在执行计划。";
  }
  if (activeTask.value.status === "waiting_confirm") {
    return activeTask.value.auto_execute
      ? "计划已生成，系统将继续自动执行。"
      : "计划已生成，等待你确认后执行。";
  }
  if (activeTask.value.status === "waiting_step_confirm") {
    return activeTask.value.status_message || "当前步骤需要确认。";
  }
  if (activeTask.value.status === "failed") {
    return activeTask.value.error_message || "任务执行失败。";
  }
  if (activeTask.value.status === "completed") {
    return activeTask.value.status_message || "任务已完成。";
  }
  return activeTask.value.status_message || "任务已接收。";
});

const showJumpToLatest = computed(() =>
  !shouldAutoFollow.value && (timelineSteps.value.length > 0 || showDraftMessage.value),
);

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
  if (composerBusy.value) return;
  await handleCreateTask();
};

const handleCreateTask = async () => {
  const trimmed = message.value.trim();
  if (!trimmed) {
    ElMessage.warning("请输入你的 Excel 需求");
    return;
  }

  creating.value = true;
  shouldAutoFollow.value = true;
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
      ElMessage.success("任务已开始处理");
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
  shouldAutoFollow.value = true;
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
  shouldAutoFollow.value = true;
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
    ElMessage.success(isBatchDelete ? "历史任务已删除" : "任务已删除");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "删除任务失败");
  }
};

const startNewTask = () => {
  stopPolling();
  shouldAutoFollow.value = true;
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
  return "未开始";
};

const stepStatus = (status) => {
  if (status === "pending") return "planning";
  return status || "planning";
};

const stepStatusLabel = (status) => {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "running") return "进行中";
  if (status === "pending") return "待执行";
  return "处理中";
};

const phaseLabel = (phase) => (phase === "planning" ? "规划" : "执行");
const stepTimeLabel = (step) => formatTime(step.ended_at || step.started_at || "");

const scrollConversationToBottom = (behavior = "smooth") => {
  const container = conversationScrollRef.value;
  if (!container) return;
  container.scrollTo({
    top: container.scrollHeight,
    behavior,
  });
};

const distanceFromBottom = () => {
  const container = conversationScrollRef.value;
  if (!container) return 0;
  return container.scrollHeight - container.scrollTop - container.clientHeight;
};

const handleConversationScroll = () => {
  shouldAutoFollow.value = distanceFromBottom() <= 72;
};

const followConversation = (behavior = "smooth", force = false) => {
  nextTick(() => {
    if (force || shouldAutoFollow.value) {
      scrollConversationToBottom(behavior);
    }
  });
};

const jumpToLatest = () => {
  shouldAutoFollow.value = true;
  followConversation("smooth", true);
};

onMounted(fetchTasks);

watch(activeTask, () => {
  ensurePolling();
}, { deep: true });

watch(
  () => [activeTaskId.value, showDraftMessage.value],
  () => {
    shouldAutoFollow.value = true;
    followConversation("auto", true);
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
