<template>
  <div class="upload-inline">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      accept=".xlsx"
      multiple
      :on-change="handleChange"
      :on-remove="handleRemove"
    >
      <el-button plain>上传 Excel</el-button>
    </el-upload>
    <div v-if="fileNames.length" class="file-pill">
      <span>已选择 {{ fileNames.length }} 个文件</span>
      <span>{{ fileNames.join("、") }}</span>
      <el-button text @click="handleRemove">移除</el-button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  fileNames: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["change"]);

const handleChange = (_, uploadFiles) => {
  emit(
    "change",
    uploadFiles.map((item) => item.raw).filter(Boolean),
  );
};

const handleRemove = () => {
  emit("change", []);
};
</script>
