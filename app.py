# ============================================================
# app.py —— B6：给 Agent 套一个聊天界面
#
# 这个文件分两半，上半是「发动机」，下半是「外壳」：
#   上半段 = B5 的发动机：大脑（大模型）+ 两只手（两个工具）+ 循环，原样搬过来
#   下半段 = B6 新装的外壳：输入框（方向盘）+ 过程面板（仪表盘）+ 对话记忆（黑板）
#
# 怎么运行：在 agent 文件夹打开终端，敲下面这行，浏览器会自动弹出页面
#   ..\.venv\Scripts\streamlit run app.py 
# ============================================================

import json                  # JSON 工具：Python 的列表/字典 和 JSON 文本互相转换用（大模型只认 JSON 文本）
import csv                   # 表格工具：写 CSV 文件用，写出来的文件 Excel / WPS 能直接打开
import requests              # 快递员：帮我们向网上的服务器（比如智谱搜索接口）发请求、收回复
import streamlit as st       # 界面库：几行代码就能把 Python 变成网页，这次界面的全部靠它
from openai import OpenAI    # 大模型客户端：智谱兼容 OpenAI 的调用格式，所以借这个库用

# 智谱的 API Key：一把钥匙开两扇门——既能调大模型，也能调它家的搜索接口
API_KEY = st.secrets["API_KEY"]   # 从密钥保险箱里取，不写死在代码里

# 创建大模型客户端。base_url 指向智谱的服务器（而不是 OpenAI 官方）
client = OpenAI(api_key=API_KEY, base_url="https://open.bigmodel.cn/api/paas/v4/")


# ============================================================
# 工具 1：联网搜索真实新闻（和 B5 完全一样，一行没改）
# 注意：这不是给"人"调用的，是给"模型"调用的——
# 模型没有手脚，它只能开口「我要用 search_news，关键词是 xx」，然后由这个函数真去搜
# ============================================================
def search_news(keyword):
    """输入一个关键词，去网上搜，返回一批候选新闻，交给模型去挑。"""
    response = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/web_search",  # 智谱搜索接口的地址（固定地址）
        headers={"Authorization": f"Bearer {API_KEY}"},     # 身份证明：把钥匙放在请求头里，服务器认钥匙不认人
        json={                                              # 请求体：告诉它搜什么、怎么搜
            "search_query": keyword,                        # 搜什么（关键词是模型自己想的，不是我们写死的）
            "search_engine": "search_pro_sogou",            # 用搜狗引擎：国内新闻质量比基础版好
            "search_intent": False,                         # 不做意图识别，我们只要原始结果
            "count": 10                                     # 一次给我 10 条候选，够模型挑了
        }
    )
    data = response.json()  # 把服务器返回的 JSON 文本，变成 Python 能操作的字典

    if "error" in data:
        # 搜索失败时，不要说崩溃，要把"出错了"如实告诉模型——
        # 模型看到错误会自己判断：换个关键词重试，还是直接放弃。这就是 Agent 的容错
        return f"搜索出错：{data['error']}"

    # 把搜索结果整理成统一的五个字段。
    # 为什么要统一？因为模型下一步要挑、要填表，字段名统一它才不会填错列
    news = [{
        "标题": i.get("title", ""),          # 新闻标题
        "来源": i.get("media") or "网络",     # 网站名；有的结果没给来源，兜底填「网络」，不留空
        "日期": i.get("publish_date", ""),   # 发布时间
        "摘要": i.get("content", ""),        # 内容摘要
        "链接": i.get("link", "")            # 原文地址（收料员场景里，链接是最重要的那列）
    } for i in data.get("search_result", [])]

    return json.dumps(news, ensure_ascii=False)  # 转成 JSON 文本交还给模型；ensure_ascii=False 是为了中文不被转成乱码字符


# ============================================================
# 工具 2：把挑好的新闻存成表格（和 B5 完全一样）
# ============================================================
def save_table(rows):
    """输入模型挑好的新闻列表，写成一个 CSV 表格文件。"""
    filename = "AI新闻收集表.csv"

    # newline="" 是 csv 模块在 Windows 上的固定写法，防止每行之间多出空行
    # encoding="utf-8-sig" 是关键：带这个标记的文件，Excel / WPS 打开才不会中文乱码
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["标题", "来源", "日期", "摘要", "链接"])  # 规定有这五列
        writer.writeheader()    # 先写表头那一行
        writer.writerows(rows)  # 再把每一行数据依次写进去

    return f"已把 {len(rows)} 条新闻写入 {filename}"  # 回话给模型：我干完了，干了多少


# ============================================================
# 工具说明书：告诉模型它有几只手、每只手能干什么、要带什么参数
#
# 模型本身不能搜索、不能写文件，它只能"看菜单点菜"。
# 这份说明书就是菜单：
#   - description 写得越清楚，模型越不容易点错菜
#   - name 必须和上面的 Python 函数名一模一样（循环里就是靠名字找到对应函数的）
# ============================================================
tools = [
    {"type": "function", "function": {
        "name": "search_news",                                   # 对应上面的 search_news 函数
        "description": "联网搜索真实新闻，返回候选新闻列表（含标题、来源、日期、摘要、链接）",
        "parameters": {"type": "object", "properties": {
            # 这个工具只要一个参数：关键词。类型是字符串
            "keyword": {"type": "string", "description": "搜索关键词，例如：AI"}
        }, "required": ["keyword"]}                              # 必填项：不填关键词不允许调用
    }},
    {"type": "function", "function": {
        "name": "save_table",                                    # 对应上面的 save_table 函数
        "description": "把整理好的新闻列表保存成 CSV 表格文件",
        "parameters": {"type": "object", "properties": {
            # 这个工具要一个参数：rows（一组新闻）。类型是数组，数组里每一项是一个小字典
            "rows": {"type": "array", "description": "要保存的新闻行",
                     "items": {"type": "object", "properties": {
                         "标题": {"type": "string"}, "来源": {"type": "string"},
                         "日期": {"type": "string"}, "摘要": {"type": "string"},
                         "链接": {"type": "string"}},
                         "required": ["标题", "来源", "日期", "摘要", "链接"]}}  # 每行这五列都不能缺
        }, "required": ["rows"]}
    }}
]

# 系统提示词 = 给它的岗位职责。每次对话开头都带着这段话，相当于入职时签的岗位说明
SYSTEM = ("你是一个会自动干活的收料员。收到任务后按「想→做→看→判断」的节奏来："
          "先用 search_news 搜新闻，看清楚结果后挑出符合要求的条数（优先挑日期新、主题不重复的），"
          "再调 save_table 存成表格，全部做完后用一句话向我汇报。")


# ============================================================
# 界面部分（B6 新增的只有这一段，从这行往下全是新东西）
# ============================================================
st.title("收料员雏形")  # 页面最上面的大标题
st.caption("你只说一句话，它自己去搜、去挑、去整理成表格。")  # 标题下面的一行灰色小字

# ---- 对话记忆：st.session_state 是 Streamlit 的「黑板」 ----
# 为什么需要黑板？网页每点一次按钮、每发一句话，整个脚本都会从头重跑一遍，
# 普通变量会被清空。只有挂在 session_state 上的东西才留得住，相当于黑板不被擦掉。
if "history" not in st.session_state:
    st.session_state.history = []   # 第一次打开页面时，黑板上什么都没写

# 把黑板上记着的旧对话，一条一条画成聊天气泡
for m in st.session_state.history:
    with st.chat_message(m["role"]):   # role 是 "user" 画在右边，"assistant" 画在左边
        st.write(m["content"])

# ---- 方向盘：底部的输入框 ----
# 用户在这里敲任务、按回车。没敲之前 task 是空的，下面整段都不会执行
task = st.chat_input("交代任务，例如：帮我收集 3 条 AI 新闻并整理成表格")

if task:  # 只有真的输入了东西，才开始干活
    # 第 1 步：把用户这句话记上黑板，并立刻画出一个用户气泡
    st.session_state.history.append({"role": "user", "content": task})
    with st.chat_message("user"):
        st.write(task)

    # 第 2 步：开始跑 Agent。所有过程都显示在"助手"这边的一个气泡里
    with st.chat_message("assistant"):
        # 组装这次要发给模型的完整对话：岗位职责 + 之前聊过的 + 这次的新任务
        messages = [{"role": "system", "content": SYSTEM}] + st.session_state.history
        final_reply = ""   # 先准备一个空位，等会儿装模型最后那句汇报

        # ---- 仪表盘：st.status 是一个可展开的面板，实时显示它正在干什么 ----
        with st.status("正在干活……", expanded=True) as status:

            # ---- 这就是 B5 那个循环，一个字没改 ----
            while True:  # 一直转，直到模型自己说"干完了"
                # 把目前全部对话 + 工具菜单发给模型，让它决定下一步
                response = client.chat.completions.create(model="glm-5.3", messages=messages, tools=tools)
                message = response.choices[0].message
                messages.append(message.model_dump())  # 模型这次的回复也记进对话（里面可能含 tool_calls）

                if message.tool_calls:
                    # 模型点菜了：把它要的每道菜（工具调用）逐个做出来
                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments)  # 参数是 JSON 文本，先转成字典
                        if tool_call.function.name == "search_news":
                            st.write(f"搜一下：{args['keyword']}")   # 面板上显示进度，让你看得见
                            result = search_news(**args)             # 真的去搜；**args 是把字典拆开当参数传进去
                        else:  # 菜单上只有两道菜，剩下的一定是 save_table
                            st.write(f"写表格：{len(args['rows'])} 行")
                            result = save_table(**args)
                        # 把工具的结果记进对话。tool_call_id 不能省：它告诉模型"这是哪一次点菜的结果"
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
                    # 这里故意不 break：自动回到 while 开头，让模型看结果、想下一步
                else:
                    # 模型没点菜、直接说话了 = 它判断任务干完了
                    final_reply = message.content
                    break  # 循环到此结束

            status.update(label="干完了", state="complete")  # 面板打个勾、收起来

        st.write(final_reply)  # 把最后那句汇报画到页面上

    # 第 3 步：把汇报也记上黑板，下次任务它还记得前面发生过什么
    st.session_state.history.append({"role": "assistant", "content": final_reply})
