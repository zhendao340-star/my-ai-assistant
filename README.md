# 收料员雏形（ShouLiaoYuan）

> 一句话介绍：你只说一句话，Agent 自动联网搜索、筛选新闻，并整理成表格。

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](在这里填你的应用链接)

## ✨ 功能演示

| 界面截图 | 说明 |
|---|---|
| （放一张截图） | 输入一句话任务 |

- 🔍 联网搜索真实新闻（智谱 web_search）
- 🤖 自动筛选：优先选日期新、主题不重复的
- 📊 结果直接展示在页面上，可下载 CSV
- 💬 多轮对话：记得之前交代过的任务

## 🚀 在线体验

直接打开：https://你的应用名.streamlit.app

## 🛠️ 技术栈

| 技术 | 用途 |
|---|---|
| Python | 主语言 |
| Streamlit | 界面 |
| 智谱 GLM（OpenAI SDK） | 大模型 |
| Function Calling | 模型自主调用工具 |
| Web Search API | 联网搜索 |

## 📂 项目结构

```
.
├── app.py            # 主程序：Agent 循环 + 界面
└── requirements.txt  # 依赖清单
```

## 🔧 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

需要配置密钥：项目根目录建 `.streamlit/secrets.toml`：

```toml
API_KEY = "你的智谱 API Key"
```

## 💡 我学到/实现的要点

- Agent 循环：模型「想→调工具→看结果→判断」直到任务完成
- 用 st.session_state 解决 Streamlit 脚本重跑导致的对话丢失
- 密钥用 st.secrets 管理，不写死在代码里
