<template>
  <HomeView />
</template>

<script setup>
import HomeView from "./views/HomeView.vue";
</script>

<style>
:root {
  color: #1f2937;
  background: #f3f4f6;
  font-family: "PingFang SC", "Noto Sans SC", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #f3f4f6;
}

#app {
  min-height: 100vh;
}

.workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
}

.history-shell {
  padding: 20px 16px;
  border-right: 1px solid #dde6ef;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.9), transparent 34%),
    linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
}

.history-top,
.history-actions,
.message-head,
.message-title-wrap,
.composer-actions,
.plan-head,
.plan-actions,
.result-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-brand {
  font-size: 18px;
  font-weight: 700;
}

.history-sub {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.history-actions {
  margin: 14px 0 14px;
}

.conversation-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.conversation-scroll {
  flex: 1;
  overflow: auto;
  padding: 24px 24px 160px;
}

.conversation-inner {
  max-width: 860px;
  margin: 0 auto;
}

.message-row {
  display: flex;
  margin-bottom: 18px;
}

.role-user {
  justify-content: flex-end;
}

.message-shell {
  width: min(100%, 760px);
}

.message-label {
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 12px;
}

.message-card {
  padding: 16px 18px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.role-user .message-card {
  background: #eef4ff;
  border-color: #d8e5ff;
}

.message-title {
  font-size: 15px;
  font-weight: 700;
}

.message-time {
  color: #94a3b8;
  font-size: 12px;
}

.user-copy,
.agent-copy,
.analysis-list,
.plan-list,
.result-meta,
.timeline-label,
.timeline-detail,
.debug-block,
.inline-json,
.welcome-card p {
  font-size: 14px;
  line-height: 1.7;
}

.user-file {
  margin-top: 8px;
  color: #4b5563;
  font-size: 13px;
}

.analysis-list {
  display: grid;
  gap: 6px;
}

.timeline-list {
  display: grid;
  gap: 10px;
}

.timeline-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.timeline-icon {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 12px;
  flex: 0 0 22px;
}

.timeline-icon.is-running {
  background: #fff3cd;
  color: #9a6700;
}

.timeline-icon.is-failed {
  background: #fdecea;
  color: #c2410c;
}

.timeline-icon.is-completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.timeline-detail {
  color: #64748b;
}

.debug-collapse,
.result-collapse,
.plan-actions .el-collapse {
  width: 100%;
}

.debug-block,
.inline-json {
  margin: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}

.plan-summary,
.result-card {
  display: grid;
  gap: 12px;
}

.plan-title,
.result-title,
.welcome-title {
  font-size: 15px;
  font-weight: 700;
}

.plan-list {
  margin: 0;
  padding-left: 18px;
}

.composer-box {
  position: sticky;
  bottom: 0;
  padding: 16px 24px 24px;
  background: linear-gradient(180deg, rgba(243, 244, 246, 0), #f3f4f6 25%);
}

.composer-surface {
  max-width: 860px;
  margin: 0 auto;
  padding: 14px;
  border: 1px solid #dbe4f0;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.upload-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.file-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  font-size: 12px;
}

.welcome-card {
  max-width: 720px;
  margin: 80px auto 0;
  padding: 28px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  text-align: center;
}

.is-error {
  border-left: 3px solid #ef4444;
  padding-left: 12px;
}

.is-success {
  border-left: 3px solid #10b981;
  padding-left: 12px;
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .history-shell {
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
  }
}
</style>
