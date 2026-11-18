# ITSupportAgent

基于 Python、FastAPI 和 DeepSeek 的本地 IT 服务台多 Agent 原型，处理设备故障、权限申请、网络问题和办公软件安装咨询。

## 功能

- 使用规则识别设备故障、权限申请、网络问题、软件安装和工单升级五类意图。
- 将请求路由到 DeviceAgent、PermissionAgent、NetworkAgent，并处理通用咨询与升级请求。
- 提取设备编号、工号和操作系统版本。
- 按会话编号保留最近对话及实体，支持跨轮追问与会话隔离。
- 查询本地演示资产表，使用关键词检索 IT 知识库。
- 通过 SQLite 保存演示工单，支持重复请求去重和按编号查询。
- 提供网页聊天界面，展示 Agent、实体和工具调用记录。

## 技术栈

Python、FastAPI、Pydantic、DeepSeek API、SQLite、HTML、CSS、JavaScript。

## 本地运行

1. 使用 Python 3.11，安装依赖：`python -m pip install -r requirements.txt`。
2. 将 `.env.example` 复制为 `.env`，填写自己的 API Key 和可用模型名称。
3. 执行：`python -m uvicorn main:app --reload --port 8001`。
4. 浏览器打开 `http://127.0.0.1:8001/`。
5. 接口文档地址：`http://127.0.0.1:8001/docs`。

## 演示流程

新建会话后，依次发送：

1. 设备编号 PC-2026-001，Windows 11，电脑无法开机。
2. 电源灯亮了，但是屏幕一直是黑的。
3. 请创建 IT 工单。

复制返回的 DEMO 工单编号，在页面查询记录；重复提交相同请求可验证工单去重。

## 实现边界

资产与知识库使用演示资料，工单保存在本机，不连接真实企业系统。意图识别和知识检索采用规则及关键词匹配，工具由代码控制调用。会话记忆保存在进程内，重启后清空；工单保存在 SQLite 中。当前未接入员工登录和权限控制，适用于本地学习与演示。