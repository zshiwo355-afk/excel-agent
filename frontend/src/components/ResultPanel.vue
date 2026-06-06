<template>
  <div class="result-card" :class="task?.status === 'failed' ? 'is-error' : 'is-success'">
    <div class="result-title">
      {{ task?.status === "failed" ? "执行失败" : "文件已生成" }}
    </div>

    <div v-if="task?.status === 'completed'" class="result-meta">
      <div>文件名：{{ fileName }}</div>
      <div>生成时间：{{ formatTime(task?.updated_at) }}</div>
      <div>下载方式：点击下方“下载 Excel”按钮，或使用页面顶部的“下载结果”按钮。</div>
    </div>

    <div v-else class="result-meta">
      <div>{{ task?.error_message || task?.error || "任务执行失败。" }}</div>
    </div>

    <div class="result-actions">
      <el-button
        v-if="task?.status === 'completed'"
        type="primary"
        tag="a"
        :href="downloadUrl"
        target="_blank"
      >
        下载 Excel
      </el-button>

      <el-collapse class="result-collapse">
        <el-collapse-item
          v-if="technicalError"
          title="查看技术详情"
          name="technical"
        >
          <pre class="inline-json">{{ technicalError }}</pre>
        </el-collapse-item>
      </el-collapse>
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
  downloadUrl: {
    type: String,
    default: "",
  },
});

const fileName = computed(
  () => props.task?.output_file_path?.split("/").pop() || "output.xlsx",
);
const technicalError = computed(() => props.task?.technical_error || "");

const formatTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};
</script>
