<template>
  <div class="upload-inline">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      accept=".xlsx"
      :on-change="handleChange"
      :on-remove="handleRemove"
    >
      <el-button plain>上传 Excel</el-button>
    </el-upload>
    <div v-if="fileName" class="file-pill">
      <span>{{ fileName }}</span>
      <el-button text @click="handleRemove">移除</el-button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  fileName: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["change"]);

const handleChange = (uploadFile) => {
  emit("change", uploadFile.raw || null);
};

const handleRemove = () => {
  emit("change", null);
};
</script>
