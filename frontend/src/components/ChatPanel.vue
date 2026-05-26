<template>
  <div class="composer-box">
    <div class="composer-surface">
      <el-input
        :model-value="message"
        type="textarea"
        :rows="3"
        resize="none"
        placeholder="描述你想让 Excel Agent 执行的任务，支持一次上传一个或多个 .xlsx 文件。"
        @update:model-value="$emit('update:message', $event)"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="composer-actions">
        <UploadPanel :file-names="fileNames" @change="$emit('file-change', $event)" />
        <el-button type="primary" :loading="loading" @click="submit">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import UploadPanel from "./UploadPanel.vue";

defineProps({
  message: {
    type: String,
    default: "",
  },
  fileNames: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit", "update:message", "file-change"]);

const submit = () => {
  emit("submit");
};
</script>
