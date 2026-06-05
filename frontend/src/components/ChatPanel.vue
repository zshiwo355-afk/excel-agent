<template>
  <div class="composer-box">
    <div class="composer-surface">
      <div class="composer-header">
        <div class="composer-title">新建任务</div>
      </div>
      <el-input
        class="composer-input"
        :model-value="message"
        type="textarea"
        :rows="3"
        resize="none"
        :placeholder="placeholder"
        @update:model-value="$emit('update:message', $event)"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="composer-actions">
        <UploadPanel v-if="allowUpload" :files="files" @change="$emit('file-change', $event)" />
        <el-button class="send-button" type="primary" :loading="loading" @click="submit">
          <el-icon><Promotion /></el-icon>
          {{ submitLabel }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Promotion } from "@element-plus/icons-vue";

import UploadPanel from "./UploadPanel.vue";

defineProps({
  message: {
    type: String,
    default: "",
  },
  files: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: "描述你想让 Excel Agent 执行的任务，支持一次上传一个或多个 .xlsx 文件。",
  },
  submitLabel: {
    type: String,
    default: "发送",
  },
  allowUpload: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["submit", "update:message", "file-change"]);

const submit = () => {
  emit("submit");
};
</script>
