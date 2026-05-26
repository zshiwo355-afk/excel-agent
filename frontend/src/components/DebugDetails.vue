<template>
  <el-collapse v-if="availableSections.length" class="debug-collapse">
    <el-collapse-item title="学习模式 / 详细过程" name="learning">
      <el-collapse>
        <el-collapse-item
          v-for="section in availableSections"
          :key="section.title"
          :title="section.title"
          :name="section.title"
        >
          <pre class="debug-block">{{ formatContent(section.content) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  sections: {
    type: Array,
    default: () => [],
  },
});

const availableSections = computed(() =>
  props.sections.filter((section) => {
    if (section.content === null || section.content === undefined) return false;
    if (Array.isArray(section.content)) return section.content.length > 0;
    if (typeof section.content === "object") return Object.keys(section.content).length > 0;
    return String(section.content).trim().length > 0;
  }),
);

const formatContent = (content) => {
  if (typeof content === "string") return content;
  return JSON.stringify(content, null, 2);
};
</script>
