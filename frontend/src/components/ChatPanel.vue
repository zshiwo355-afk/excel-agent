<template>
  <div class="composer-box">
    <div class="composer-surface">
      <el-input
        :model-value="message"
        type="textarea"
        :rows="3"
        resize="none"
        placeholder="描述你想让 Excel Agent 执行的任务。支持上传 .xlsx 后修改。"
        @update:model-value="$emit('update:message', $event)"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="composer-actions">
        <UploadPanel :file-name="fileName" @change="$emit('file-change', $event)" />
        <el-button type="primary" :loading="loading" @click="submit">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import UploadPanel from "./UploadPanel.vue";

const props = defineProps({
  message: {
    type: String,
    default: "",
  },
  fileName: {
    type: String,
    default: "",
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
