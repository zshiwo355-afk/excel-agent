<template>
  <div class="plan-summary">
    <div class="plan-head">
      <div class="plan-title">任务拆解</div>
      <el-tag size="small" type="warning" effect="plain">{{ task?.status }}</el-tag>
    </div>

    <div class="plan-list">
      <div>目标：{{ task?.task_plan?.goal }}</div>
      <div v-if="task?.task_plan?.assumptions?.length">假设：{{ task.task_plan.assumptions.join("；") }}</div>
      <div v-if="task?.task_plan?.risks?.length">风险：{{ task.task_plan.risks.join("；") }}</div>
    </div>

    <el-collapse>
      <el-collapse-item
        v-for="step in task?.task_plan?.steps || []"
        :key="step.step_id"
        :title="`${step.step_id} · ${step.title} · ${step.status || 'pending'}`"
        :name="step.step_id"
      >
        <div class="plan-list">
          <div>类型：{{ step.step_type }}</div>
          <div>说明：{{ step.description }}</div>
          <div v-if="step.input_artifact">输入工件：{{ step.input_artifact }}</div>
          <div v-if="step.output_artifact">输出工件：{{ step.output_artifact }}</div>
          <div v-if="step.requires_user_confirm">需要确认：是</div>
          <div v-if="step.error">错误：{{ step.error }}</div>
        </div>
        <pre class="inline-json">{{ formatJson({ params: step.params, validation: step.validation, validation_result: step.validation_result }) }}</pre>
      </el-collapse-item>
    </el-collapse>

    <div class="plan-actions">
      <el-button
        v-if="task?.status === 'waiting_confirm' || task?.status === 'waiting_step_confirm'"
        type="primary"
        :loading="confirmLoading"
        @click="$emit('confirm')"
      >
        {{ task?.status === "waiting_step_confirm" ? "确认继续" : "确认执行" }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  task: {
    type: Object,
    default: null,
  },
  confirmLoading: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["confirm"]);

const formatJson = (value) => JSON.stringify(value, null, 2);
</script>
