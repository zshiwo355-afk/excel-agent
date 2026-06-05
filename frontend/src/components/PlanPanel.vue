<template>
  <div class="plan-summary">
    <div class="plan-head">
      <div class="plan-title">执行计划</div>
      <el-tag size="small" :type="statusType" effect="plain">{{ displayStatus }}</el-tag>
    </div>

    <ol v-if="isMergePlan" class="plan-list">
      <li>合并方式：纵向追加</li>
      <li>目标 sheet：{{ mergePlan?.target_sheet_name || "合并明细" }}</li>
      <li>来源文件数量：{{ task?.uploaded_files?.length || task?.uploaded_file_paths?.length || 0 }}</li>
      <li>来源 sheet 数量：{{ mergePlan?.source_sheets?.length || 0 }}</li>
      <li>是否增加来源列：{{ mergePlan?.add_source_columns ? "是" : "否" }}</li>
      <li>字段对齐方式：{{ mappingMode }}</li>
      <li v-if="task?.excel_plan?.notes?.length">备注：{{ task.excel_plan.notes.join("；") }}</li>
    </ol>

    <ol v-else class="plan-list">
      <template v-if="isSplitPlan">
        <li>操作类型：按字段拆分 sheet</li>
        <li>源 sheet：{{ targetSheet }}</li>
        <li>拆分字段：{{ primarySheet?.split?.column || "-" }}</li>
        <li>输出方式：每个字段值一个 sheet</li>
      </template>
      <template v-else>
      <li>操作文件：{{ fileLabel }}</li>
      <template v-for="(sheet, index) in sheetPlans" :key="`${sheet.operation}-${index}`">
        <li>步骤 {{ index + 1 }}：{{ operationLabelFor(sheet) }}</li>
        <li>目标 sheet：{{ targetSheetFor(sheet) }}</li>
        <li v-if="dateUpdateLabelFor(sheet)">目标修改：{{ dateUpdateLabelFor(sheet) }}</li>
        <li v-if="fillLabelFor(sheet)">写入字段：{{ fillLabelFor(sheet) }}</li>
        <li v-if="sortLabelFor(sheet)">排序字段：{{ sortLabelFor(sheet) }}</li>
        <li v-if="orderLabelFor(sheet)">排序方向：{{ orderLabelFor(sheet) }}</li>
        <li v-if="styleLabelsFor(sheet).length">格式化：{{ styleLabelsFor(sheet).join("、") }}</li>
        <li v-if="cleanLabelsFor(sheet).length">清洗：{{ cleanLabelsFor(sheet).join("、") }}</li>
      </template>
      <li v-if="task?.excel_plan?.notes?.length">备注：{{ task.excel_plan.notes.join("；") }}</li>
      </template>
    </ol>

    <div class="plan-actions">
      <el-button
        v-if="task?.status === 'waiting_confirm' && task?.auto_execute === false"
        type="primary"
        :loading="confirmLoading"
        @click="$emit('confirm')"
      >
        确认生成
      </el-button>
      <el-collapse>
        <el-collapse-item title="查看计划 JSON" name="plan-json">
          <pre class="inline-json">{{ formatJson(task?.excel_plan) }}</pre>
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
  confirmLoading: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["confirm"]);

const isMergePlan = computed(() => props.task?.excel_plan?.action === "merge_workbooks");
const isSplitPlan = computed(() => primarySheet.value?.operation === "split_sheet_by_column");
const mergePlan = computed(() => props.task?.excel_plan?.merge || null);
const sheetPlans = computed(() => props.task?.excel_plan?.sheets || []);
const primarySheet = computed(() => props.task?.excel_plan?.sheets?.[0] || null);
const displayStatus = computed(() => props.task?.excel_plan ? "completed" : "pending");
const statusType = computed(() => displayStatus.value === "completed" ? "success" : "info");

const fileLabel = computed(() => {
  return props.task?.uploaded_file_path?.split("/").pop() || props.task?.excel_plan?.workbook_name || "新建工作簿";
});

const targetSheet = computed(() => {
  return primarySheet.value?.source_sheet || primarySheet.value?.name || "未指定";
});

const mappingMode = computed(() =>
  mergePlan.value?.column_mapping && Object.keys(mergePlan.value.column_mapping).length
    ? "字段映射"
    : "字段并集",
);

const operationMap = {
  format_and_sort_sheet: "格式化并排序",
  format_sheet: "格式化表格",
  sort_rows: "排序数据",
  create_summary_sheet: "生成汇总表",
  clean_sheet: "清洗表格",
  create_sheet: "新建工作表",
  append_columns: "新增字段",
  split_sheet_by_column: "按字段拆分 sheet",
  update_date_month: "修改日期字段",
  fill_column_with_value: "写入字段值",
};

const operationLabelFor = (sheet) => operationMap[sheet?.operation] || "执行任务";
const targetSheetFor = (sheet) => sheet?.source_sheet || sheet?.name || "未指定";
const sortLabelFor = (sheet) => sheet?.sort?.column || "";
const orderLabelFor = (sheet) => {
  if (!sheet?.sort?.order) return "";
  return sheet.sort.order === "desc" ? "从高到低 / 降序" : "从低到高 / 升序";
};

const styleLabelsFor = (sheet) => {
  const style = sheet?.style || {};
  return [
    style.freeze_header ? "冻结表头" : "",
    style.auto_filter ? "开启筛选" : "",
    style.auto_width ? "自动列宽" : "",
    style.header_bold ? "表头加粗" : "",
  ].filter(Boolean);
};

const cleanLabelsFor = (sheet) => {
  const clean = sheet?.clean || {};
  return [
    clean.remove_empty_rows ? "删除空行" : "",
    clean.trim_text ? "去除文本空格" : "",
  ].filter(Boolean);
};

const dateUpdateLabelFor = (sheet) => {
  const plan = sheet?.date_update;
  if (!plan?.target_month) return "";
  return `将日期月份修改为 ${plan.target_month} 月`;
};

const fillLabelFor = (sheet) => {
  const plan = sheet?.fill;
  if (!plan?.column_name) return "";
  if (plan.value_mode === "today_date") {
    return `${plan.column_name} = 今天日期`;
  }
  if (plan.value_mode === "today_datetime") {
    return `${plan.column_name} = 当前时间`;
  }
  if (plan.value_mode === "static_text") {
    return `${plan.column_name} = ${plan.static_value || ""}`;
  }
  return plan.column_name;
};

const formatJson = (value) => {
  if (!value) return "暂无";
  return JSON.stringify(value, null, 2);
};
</script>
