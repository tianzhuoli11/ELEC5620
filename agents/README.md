# 共享 Agent 与编排

放置全组共用的 `HomeCoordinatorAgent`、`MonitoringAgent`、`DeviceAutomationAgent` 和 LangGraph 状态图、任务分发、确认/超时及结果汇总。Yuanbo Zhang 整合框架，其他成员提供各场景入口与测试。

后续文件可命名为 `coordinator.py`、`monitoring.py`、`automation.py`、`graph.py`，实际实现时再创建。共享类型从 `models/` 导入，领域逻辑从 `domains/` 调用，LLM/通知/日志从 `services/` 调用，设备操作通过 `tools/`。

不放 Streamlit 页面，不为每个业务域复制三个 Agent。实际返回状态经验证后才报告设备动作成功。
