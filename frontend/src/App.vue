<template>
  <HomeView />
</template>

<script setup>
import HomeView from "./views/HomeView.vue";
</script>

<style>
:root {
  color: #172033;
  background: #f4efe7;
  font-family: "PingFang SC", "Noto Sans SC", sans-serif;
  --page-bg: #f4efe7;
  --panel-bg: rgba(255, 251, 246, 0.9);
  --panel-border: rgba(111, 126, 146, 0.16);
  --panel-shadow: 0 24px 60px rgba(41, 51, 70, 0.08);
  --text-strong: #182133;
  --text-base: #3b4658;
  --text-muted: #6c7484;
  --accent: #0f766e;
  --accent-soft: rgba(15, 118, 110, 0.12);
  --accent-strong: #9f4d2f;
  --sidebar-bg: #101826;
  --sidebar-border: rgba(203, 213, 225, 0.08);
}

* {
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  margin: 0;
  color: var(--text-base);
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.62), transparent 30%),
    linear-gradient(180deg, #f8f2ea 0%, var(--page-bg) 38%, #efe8dd 100%);
  overflow: hidden;
}

#app {
  height: 100%;
}

a {
  color: inherit;
}

.el-button,
.el-tag,
.el-collapse-item__header,
.el-collapse-item__content,
.el-input__inner,
.el-textarea__inner {
  font-family: inherit;
}

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
}

.history-shell {
  position: relative;
  padding: 24px 18px;
  border-right: 1px solid var(--sidebar-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 22%),
    linear-gradient(180deg, #111827 0%, var(--sidebar-bg) 100%);
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
  color: #f8fafc;
  font-family: "Songti SC", "STSong", serif;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0;
}

.history-sub {
  margin-top: 6px;
  color: rgba(203, 213, 225, 0.72);
  font-size: 12px;
}

.history-actions {
  margin: 14px 0 18px;
}

.history-actions .el-button,
.history-top .el-button {
  --el-button-text-color: #f8fafc;
  --el-button-bg-color: rgba(255, 255, 255, 0.04);
  --el-button-border-color: rgba(255, 255, 255, 0.08);
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.08);
  --el-button-hover-border-color: rgba(94, 234, 212, 0.36);
  --el-button-active-bg-color: rgba(255, 255, 255, 0.1);
  font-weight: 600;
}

.history-top .el-button--primary {
  --el-button-bg-color: #ecfdf5;
  --el-button-border-color: #ecfdf5;
  --el-button-text-color: #0f172a;
  --el-button-hover-bg-color: #d1fae5;
  --el-button-hover-border-color: #d1fae5;
}

.conversation-panel {
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.12), transparent 20%),
    transparent;
}

.conversation-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
  padding: 32px 28px 36px;
}

.conversation-inner {
  max-width: 820px;
  margin: 0 auto;
}

.workspace-hero {
  display: grid;
  gap: 22px;
  margin-bottom: 28px;
  padding: 28px 30px;
  border: 1px solid var(--panel-border);
  border-radius: 30px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.86), rgba(255, 249, 243, 0.76)),
    var(--panel-bg);
  box-shadow: var(--panel-shadow);
}

.task-hero {
  display: grid;
  gap: 16px;
  margin-bottom: 20px;
  padding: 0 0 18px;
  border-bottom: 1px solid rgba(111, 126, 146, 0.16);
}

.task-hero-copy {
  display: grid;
  gap: 8px;
}

.task-hero-main,
.task-hero-side {
  display: grid;
  gap: 12px;
}

.task-hero-title {
  margin: 0;
  color: var(--text-strong);
  font-family: "Songti SC", "STSong", serif;
  font-size: 28px;
  line-height: 1.24;
  font-weight: 700;
}

.task-hero-description {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.7;
}

.task-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.task-hero-stat {
  display: grid;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(111, 126, 146, 0.1);
}

.task-hero-actions {
  display: flex;
  justify-content: flex-start;
}

.hero-download-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 16px;
  border-radius: 999px;
  background: #123b3a;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.hero-download-link:hover {
  background: #19514f;
}

.workspace-hero.is-empty {
  padding-bottom: 32px;
}

.hero-copy {
  max-width: 760px;
}

.hero-kicker {
  margin-bottom: 12px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-title {
  margin: 0;
  color: var(--text-strong);
  font-family: "Songti SC", "STSong", serif;
  font-size: 38px;
  line-height: 1.18;
  font-weight: 700;
}

.hero-description {
  max-width: 720px;
  margin: 14px 0 0;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 1.75;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-stat {
  display: grid;
  gap: 10px;
  min-height: 104px;
  padding: 18px;
  border: 1px solid rgba(111, 126, 146, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.42);
}

.hero-stat-label {
  color: var(--text-muted);
  font-size: 12px;
}

.hero-stat-value {
  color: var(--text-strong);
  font-size: 26px;
  line-height: 1.15;
  font-weight: 700;
}

.hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.message-row {
  display: flex;
  margin-bottom: 14px;
}

.role-user {
  justify-content: flex-end;
}

.message-shell {
  width: min(100%, 820px);
}

.message-label {
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.message-card {
  padding: 4px 0 14px 18px;
  border: 0;
  border-left: 2px solid rgba(111, 126, 146, 0.18);
  background: transparent;
  border-radius: 0;
  box-shadow: none;
  backdrop-filter: none;
}

.role-user .message-card {
  border-left-color: rgba(15, 118, 110, 0.36);
}

.message-title {
  color: var(--text-strong);
  font-size: 16px;
  font-weight: 700;
}

.message-time {
  color: rgba(108, 116, 132, 0.88);
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
.welcome-panel p,
.welcome-item span {
  font-size: 14px;
  line-height: 1.7;
}

.user-file {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.step-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.step-phase-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
}

.step-status-copy {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.step-result {
  color: var(--text-strong);
}

.analysis-list {
  display: grid;
  gap: 8px;
}

.timeline-list {
  display: grid;
  gap: 14px;
}

.timeline-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.timeline-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 28px;
}

.timeline-icon.is-running {
  background: rgba(251, 191, 36, 0.16);
  color: #a16207;
}

.timeline-icon.is-failed {
  background: rgba(248, 113, 113, 0.14);
  color: #b91c1c;
}

.timeline-icon.is-completed {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.timeline-label {
  color: var(--text-strong);
  font-weight: 600;
}

.timeline-detail {
  color: var(--text-muted);
}

.debug-collapse,
.result-collapse,
.plan-actions .el-collapse {
  width: 100%;
}

.el-collapse {
  --el-collapse-border-color: rgba(111, 126, 146, 0.14);
  border-top: 1px solid rgba(111, 126, 146, 0.14);
  border-bottom: 1px solid rgba(111, 126, 146, 0.14);
}

.el-collapse-item__header {
  height: auto;
  min-height: 48px;
  color: var(--text-strong);
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.el-collapse-item__wrap {
  background: transparent;
}

.debug-block,
.inline-json {
  margin: 0;
  padding: 14px 16px;
  color: var(--text-base);
  background: rgba(250, 246, 240, 0.5);
  border: 1px solid rgba(111, 126, 146, 0.08);
  border-radius: 10px;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}

.plan-summary,
.result-card {
  display: grid;
  gap: 14px;
}

.plan-title,
.result-title,
.welcome-title {
  color: var(--text-strong);
  font-size: 16px;
  font-weight: 700;
}

.plan-list {
  margin: 0;
  padding-left: 20px;
  color: var(--text-base);
}

.plan-list > * + * {
  margin-top: 6px;
}

.result-card {
  padding: 2px 0 0;
}

.result-meta {
  color: var(--text-base);
}

.plan-actions .el-button--primary,
.result-actions .el-button--primary,
.send-button {
  --el-button-bg-color: #123b3a;
  --el-button-border-color: #123b3a;
  --el-button-hover-bg-color: #19514f;
  --el-button-hover-border-color: #19514f;
  --el-button-active-bg-color: #0e2f2f;
  --el-button-active-border-color: #0e2f2f;
  --el-button-text-color: #f8fafc;
}

.plan-actions .el-button,
.result-actions .el-button,
.send-button,
.upload-button {
  border-radius: 999px;
  font-weight: 600;
}

.result-actions,
.composer-actions {
  flex-wrap: wrap;
}

.composer-box {
  position: sticky;
  bottom: 0;
  padding: 20px 28px 28px;
  background: linear-gradient(180deg, rgba(244, 239, 231, 0), rgba(244, 239, 231, 0.94) 22%, var(--page-bg) 48%);
}

.jump-latest {
  position: absolute;
  right: 36px;
  bottom: 178px;
  z-index: 5;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(18, 59, 58, 0.16);
  border-radius: 999px;
  background: rgba(255, 252, 248, 0.96);
  color: #123b3a;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(41, 51, 70, 0.08);
  cursor: pointer;
}

.jump-latest:hover {
  background: #ffffff;
}

.composer-surface {
  max-width: 960px;
  margin: 0 auto;
  padding: 18px;
  border-top: 1px solid rgba(111, 126, 146, 0.16);
  background: rgba(255, 252, 248, 0.86);
  border-radius: 0;
  box-shadow: none;
  backdrop-filter: none;
}

.composer-header {
  margin-bottom: 12px;
}

.composer-title {
  color: var(--text-strong);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.upload-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.composer-input .el-textarea__inner {
  min-height: 120px;
  padding: 16px 18px;
  color: var(--text-strong);
  background: rgba(255, 255, 255, 0.78);
  border-radius: 20px;
  box-shadow: none;
  --el-input-border-color: rgba(111, 126, 146, 0.16);
  --el-input-hover-border-color: rgba(15, 118, 110, 0.28);
  --el-input-focus-border-color: rgba(15, 118, 110, 0.52);
}

.composer-input.is-compact .el-textarea__inner {
  min-height: 52px;
  padding-top: 14px;
  padding-bottom: 14px;
}

.composer-input .el-textarea__inner::placeholder {
  color: #8b93a4;
}

.file-pill {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 42px;
  padding: 6px 10px 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(111, 126, 146, 0.12);
  font-size: 12px;
}

.file-pill-label {
  color: var(--text-muted);
  font-weight: 600;
}

.file-name-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  max-width: 100%;
}

.file-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.14);
  color: var(--accent);
  cursor: pointer;
}

.file-chip-remove:hover {
  background: rgba(15, 118, 110, 0.22);
}

.file-pill-action {
  padding: 0 6px;
}

.upload-button {
  --el-button-text-color: var(--text-strong);
  --el-button-bg-color: rgba(255, 255, 255, 0.78);
  --el-button-border-color: rgba(111, 126, 146, 0.14);
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.92);
  --el-button-hover-border-color: rgba(15, 118, 110, 0.24);
}

.send-button {
  min-width: 112px;
}

.welcome-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 24px;
  align-items: start;
  padding: 4px 2px 0;
}

.welcome-copy p {
  max-width: 520px;
  margin: 12px 0 0;
  color: var(--text-muted);
}

.welcome-grid {
  display: grid;
  gap: 12px;
}

.welcome-item {
  display: grid;
  gap: 6px;
  padding: 18px 20px;
  border: 1px solid rgba(111, 126, 146, 0.12);
  border-radius: 18px;
  background: rgba(255, 252, 248, 0.58);
}

.welcome-item strong {
  color: var(--text-strong);
  font-size: 15px;
}

.welcome-item span {
  color: var(--text-muted);
}

.file-pill {
  max-width: 100%;
}

.is-error {
  border-left: 3px solid #ef4444;
  padding-left: 12px;
}

.is-success {
  border-left: 3px solid #10b981;
  padding-left: 12px;
}

.el-tag {
  border-radius: 999px;
  font-weight: 600;
}

.el-empty {
  --el-empty-fill-color-0: rgba(255, 255, 255, 0.02);
  --el-empty-fill-color-1: rgba(255, 255, 255, 0.06);
  --el-empty-fill-color-2: rgba(255, 255, 255, 0.08);
  --el-empty-fill-color-3: rgba(255, 255, 255, 0.1);
  --el-empty-fill-color-4: rgba(255, 255, 255, 0.12);
  --el-empty-fill-color-5: rgba(255, 255, 255, 0.14);
  --el-empty-fill-color-6: rgba(255, 255, 255, 0.16);
  --el-empty-fill-color-7: rgba(255, 255, 255, 0.18);
  --el-empty-fill-color-8: rgba(255, 255, 255, 0.2);
  --el-empty-fill-color-9: rgba(255, 255, 255, 0.24);
  --el-empty-fill-color-10: rgba(255, 255, 255, 0.28);
  --el-empty-fill-color-11: rgba(255, 255, 255, 0.34);
  --el-empty-fill-color-12: rgba(255, 255, 255, 0.4);
  --el-empty-fill-color-13: rgba(255, 255, 255, 0.48);
  color: rgba(226, 232, 240, 0.72);
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
    height: auto;
    overflow: auto;
  }

  .history-shell {
    border-right: none;
    border-bottom: 1px solid rgba(111, 126, 146, 0.14);
    height: auto;
  }

  .conversation-panel {
    height: auto;
    min-height: 0;
    overflow: visible;
  }

  .hero-title {
    font-size: 32px;
  }

  .hero-stats,
  .task-hero-stats,
  .welcome-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .history-shell {
    padding: 18px 14px;
  }

  .history-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .conversation-scroll {
    padding: 18px 16px 24px;
  }

  .conversation-inner,
  .composer-surface {
    max-width: 100%;
  }

  .workspace-hero,
  .task-hero,
  .message-card,
  .composer-surface {
    border-radius: 0;
  }

  .workspace-hero {
    padding: 22px 20px;
  }

  .hero-title {
    font-size: 28px;
  }

  .task-hero-title {
    font-size: 24px;
  }

  .hero-stat {
    min-height: 88px;
  }

  .composer-box {
    padding: 16px 16px 20px;
  }

  .file-pill {
    align-items: flex-start;
    border-radius: 18px;
  }

  .jump-latest {
    right: 20px;
    bottom: 156px;
  }
}
</style>
