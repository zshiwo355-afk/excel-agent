<template>
  <div class="upload-inline">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      :file-list="uploadList"
      accept=".xlsx"
      multiple
      :on-change="handleChange"
    >
      <el-button class="upload-button" plain>
        <el-icon><FolderOpened /></el-icon>
        <span>上传 Excel</span>
      </el-button>
    </el-upload>
    <div v-if="fileNames.length" class="file-pill">
      <span class="file-pill-label">已选择 {{ fileNames.length }} 个文件</span>
      <span
        v-for="(name, index) in fileNames"
        :key="`${name}-${index}`"
        class="file-name-chip"
      >
        <span class="file-name-text">{{ name }}</span>
        <button
          type="button"
          class="file-chip-remove"
          aria-label="删除文件"
          @click="handleRemoveAt(index)"
        >
          <el-icon><Close /></el-icon>
        </button>
      </span>
      <el-button class="file-pill-action" text @click="handleClear">清空</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Close, FolderOpened } from "@element-plus/icons-vue";

const props = defineProps({
  files: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["change"]);
const fileNames = computed(() => props.files.map((item) => item?.name).filter(Boolean));
const uploadList = computed(() =>
  props.files.map((file, index) => ({
    name: file?.name || `file-${index + 1}`,
    uid: `${file?.name || "file"}-${index}`,
  })),
);

const handleChange = (_, uploadFiles) => {
  emit(
    "change",
    uploadFiles.map((item) => item.raw).filter(Boolean),
  );
};

const handleRemoveAt = (index) => {
  emit(
    "change",
    props.files.filter((_, currentIndex) => currentIndex !== index),
  );
};

const handleClear = () => {
  emit("change", []);
};
</script>
