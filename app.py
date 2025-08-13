import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import csv
from typing import Optional
import base64

# 页面配置
st.set_page_config(
    page_title="智谱AI Batch API 工具",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%);
    padding: 2rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.section-header {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #06b6d4;
    margin: 1rem 0;
}
.success-box {
    background-color: #d1fae5;
    border: 1px solid #10b981;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}
.error-box {
    background-color: #fee2e2;
    border: 1px solid #ef4444;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# 智谱AI API配置
ZHIPU_API_BASE = 'https://open.bigmodel.cn/api/paas/v4'

def create_batch_request(api_key: str, model: str, csv_data: list, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float, top_p: float):
    """创建批处理请求"""
    try:
        # 生成JSONL内容
        jsonl_lines = []
        for index, content in enumerate(csv_data):
            messages = []
            
            # 添加系统提示词
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 添加用户提示词，替换占位符
            final_user_prompt = user_prompt.replace('{content}', content)
            messages.append({
                "role": "user",
                "content": final_user_prompt
            })
            
            request_data = {
                "custom_id": f"request-{index + 1}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p
                }
            }
            
            jsonl_lines.append(json.dumps(request_data, ensure_ascii=False))
        
        jsonl_content = '\n'.join(jsonl_lines)
        
        # 创建batch请求
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 首先上传文件
        files = {
            'file': ('batch_requests.jsonl', jsonl_content, 'application/jsonl'),
            'purpose': (None, 'batch')
        }
        
        upload_response = requests.post(
            f'{ZHIPU_API_BASE}/files',
            headers={'Authorization': f'Bearer {api_key}'},
            files=files
        )
        
        if upload_response.status_code != 200:
            return None, f"文件上传失败: {upload_response.text}"
        
        file_data = upload_response.json()
        file_id = file_data['id']
        
        # 创建batch任务
        batch_data = {
            "input_file_id": file_id,
            "endpoint": "/v4/chat/completions",
            "completion_window": "24h"
        }
        
        batch_response = requests.post(
            f'{ZHIPU_API_BASE}/batches',
            headers=headers,
            json=batch_data
        )
        
        if batch_response.status_code == 200:
            result = batch_response.json()
            return result['id'], None
        else:
            return None, f"批处理任务创建失败: {batch_response.text}"
            
    except Exception as e:
        return None, f"创建批处理任务时发生错误: {str(e)}"

def check_batch_status(api_key: str, batch_id: str):
    """检查批处理状态"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        response = requests.get(
            f'{ZHIPU_API_BASE}/batches/{batch_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"查询失败: {response.text}"
            
    except Exception as e:
        return None, f"查询批处理状态时发生错误: {str(e)}"

def download_batch_results_by_batch_id(api_key: str, batch_id: str):
    """通过batch_id下载批处理结果"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        # 先获取batch信息
        batch_response = requests.get(
            f'{ZHIPU_API_BASE}/batches/{batch_id}',
            headers=headers
        )
        
        if batch_response.status_code != 200:
            return None, f"获取batch信息失败: {batch_response.text}"
            
        batch_data = batch_response.json()
        
        if batch_data.get('status') != 'completed':
            return None, f"任务状态: {batch_data.get('status')}，请等待完成后再下载"
            
        output_file_id = batch_data.get('output_file_id')
        if not output_file_id:
            return None, "没有输出文件"
        
        # 下载结果文件
        file_response = requests.get(
            f'{ZHIPU_API_BASE}/files/{output_file_id}/content',
            headers=headers
        )
        
        if file_response.status_code == 200:
            return file_response.text, None
        else:
            return None, f"下载失败: {file_response.text}"
            
    except Exception as e:
        return None, f"下载批处理结果时发生错误: {str(e)}"

def download_batch_results(api_key: str, file_id: str):
    """下载批处理结果（通过文件ID）"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        response = requests.get(
            f'{ZHIPU_API_BASE}/files/{file_id}/content',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.text, None
        else:
            return None, f"下载失败: {response.text}"
            
    except Exception as e:
        return None, f"下载批处理结果时发生错误: {str(e)}"

def parse_csv_data(uploaded_file):
    """解析CSV文件数据"""
    try:
        # 使用pandas读取CSV文件，模拟Node.js csv-parser的行为
        uploaded_file.seek(0)  # 重置文件指针
        df = pd.read_csv(uploaded_file, header=None, dtype=str, keep_default_na=False)
        
        data = []
        total_rows = len(df)
        skipped_rows = 0
        
        for index, row in df.iterrows():
            # 获取第一列的值（模拟Object.values(row)[0]）
            first_column = row.iloc[0] if len(row) > 0 else ''
            
            # 检查是否为有效内容（模拟Node.js的条件判断）
            if first_column and str(first_column).strip():
                data.append(str(first_column).strip())
            else:
                skipped_rows += 1
        
        return data, None, total_rows, skipped_rows
    except Exception as e:
        return None, f"解析CSV文件失败: {str(e)}", 0, 0

# 初始化session state
if 'batch_id' not in st.session_state:
    st.session_state.batch_id = ''
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'query_batch_id' not in st.session_state:
    st.session_state.query_batch_id = ''
if 'download_batch_id' not in st.session_state:
    st.session_state.download_batch_id = ''

# 主界面
with st.sidebar:
    # 标题
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    ">
        <h3 style="margin: 0; font-size: 1.2rem;">🤖 智谱AI Batch API 工具</h3>
        <p style="margin: 0.3rem 0 0 0; font-size: 0.8rem; opacity: 0.9;">批量处理文本数据，高效调用智谱AI API</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API配置
    st.subheader("🔑 API 配置")
    api_key = st.text_input("智谱AI API Key", value=st.session_state.api_key, type="password", help="请输入您的智谱AI API Key", key="sidebar_api_key")
    st.session_state.api_key = api_key
    
    # 显示当前Batch ID
    if st.session_state.batch_id:
        st.subheader("📋 当前任务")
        st.info(f"**Batch ID:** {st.session_state.batch_id}")
        if st.button("🗑️ 清除记录", help="清除当前保存的Batch ID"):
            st.session_state.batch_id = ''
            st.rerun()
    
    # 功能导航
    st.subheader("📋 功能导航")
    tab_selection = st.radio(
        "选择功能",
        ["📤 创建批处理", "📊 查询状态", "📥 下载结果"],
        index=0
    )

# 主内容区域
if tab_selection == "📤 创建批处理":
    st.header("📤 创建批处理任务")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🤖 模型参数")
        model = st.selectbox(
            "模型",
            ["GLM-4-Air-250414", "GLM-4-Flash",],
            index=0
        )
        
        max_tokens = st.slider("最大输出长度", 1, 4096, 2048)
        temperature = st.slider("温度", 0.0, 1.0, 0.7, 0.1)
        top_p = st.slider("Top P", 0.0, 1.0, 0.9, 0.1)
    
    with col2:
        st.subheader("📝 提示词设置")
        system_prompt = st.text_area(
            "系统提示词（可选）",
            placeholder="设置AI的角色和行为...",
            height=150
        )
        
        user_prompt = st.text_area(
            "用户提示词",
            placeholder="使用 {content} 作为CSV内容的占位符",
            height=150,
            help="使用 {content} 作为CSV内容的占位符"
        )
    
    st.subheader("📁 表格文件上传")
    uploaded_file = st.file_uploader(
        "选择CSV文件或拖拽上传",
        type=['csv'],
        help="请上传包含待处理文本的CSV文件，系统将读取第一列数据"
    )
    
    if uploaded_file:
        # 预览CSV内容
        csv_data, error, total_rows, skipped_rows = parse_csv_data(uploaded_file)
        if csv_data:
            st.success(f"✅ 文件解析成功，共 {len(csv_data)} 条有效数据")
            
            with st.expander("📋 预览数据（前3条）"):
                for i, content in enumerate(csv_data[:3]):
                    # 显示内容的前200个字符，避免界面过长
                    preview_content = content[:200] + "..." if len(content) > 200 else content
                    st.write(f"{i+1}. {preview_content}")
                if len(csv_data) > 3:
                    st.write(f"... 还有 {len(csv_data) - 3} 条数据")
                    
            
        else:
            st.error(f"❌ {error}")
    
    # 创建任务按钮
    if st.button("🚀 创建批处理任务", type="primary", use_container_width=True):
        if not api_key:
            st.error("请输入API Key")
        elif not uploaded_file:
            st.error("请上传CSV文件")
        else:
            csv_data, error, _, _ = parse_csv_data(uploaded_file)
            if error:
                st.error(f"❌ {error}")
            else:
                with st.spinner("正在创建批处理任务..."):
                    batch_id, error = create_batch_request(
                        api_key, model, csv_data, system_prompt, user_prompt,
                        max_tokens, temperature, top_p
                    )
                    
                    if batch_id:
                        st.session_state.batch_id = batch_id
                        st.markdown(f"""
                        <div class="success-box">
                            <h4>✅ 任务创建成功！</h4>
                            <p><strong>Batch ID:</strong> {batch_id}</p>
                            <p>任务已提交，请在"查询状态"页面查看进度</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 保存到session state
                        st.session_state.batch_id = batch_id
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            <h4>❌ 创建失败</h4>
                            <p>{error}</p>
                        </div>
                        """, unsafe_allow_html=True)

elif tab_selection == "📊 查询状态":
    st.header("📊 查询批处理状态")
    
    # 输入Batch ID
    batch_id_input = st.text_input(
        "Batch ID",
        value=st.session_state.query_batch_id,
        help="输入要查询的批处理任务ID",
        key="query_batch_id_input"
    )
    st.session_state.query_batch_id = batch_id_input
    
    # 快速填入当前任务ID
    if st.session_state.batch_id and st.button("📋 使用当前任务ID"):
        st.session_state.query_batch_id = st.session_state.batch_id
        st.rerun()
    
    if st.button("🔍 查询状态", type="primary"):
        if not api_key:
            st.error("请输入API Key")
        elif not batch_id_input:
            st.error("请输入Batch ID")
        else:
            with st.spinner("正在查询状态..."):
                result, error = check_batch_status(api_key, batch_id_input)
                
                if result:
                    status = result.get('status', 'unknown')
                    
                    # 状态颜色映射
                    status_colors = {
                        'validating': '🟡',
                        'in_progress': '🔵', 
                        'finalizing': '🟠',
                        'completed': '🟢',
                        'failed': '🔴',
                        'expired': '⚫',
                        'cancelled': '⚪'
                    }
                    
                    status_color = status_colors.get(status, '❓')
                    
                    st.markdown(f"""
                    <div class="section-header">
                        <h4>{status_color} 任务状态: {status}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 显示详细信息
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**创建时间:** {result.get('created_at', 'N/A')}")
                        st.write(f"**输入文件ID:** {result.get('input_file_id', 'N/A')}")
                        
                    with col2:
                        st.write(f"**请求数量:** {result.get('request_counts', {}).get('total', 0)}")
                        st.write(f"**完成数量:** {result.get('request_counts', {}).get('completed', 0)}")
                    
                    # 如果任务完成，显示下载按钮
                    if status == 'completed' and result.get('output_file_id'):
                        st.success("✅ 任务已完成！")
                        st.session_state.output_file_id = result['output_file_id']
                        st.info("💡 请前往'下载结果'页面获取处理结果")
                    
                    elif status == 'failed':
                        st.error("❌ 任务执行失败")
                        if 'errors' in result:
                            st.write("错误信息:", result['errors'])
                    
                    elif status in ['validating', 'in_progress', 'finalizing']:
                        st.info("⏳ 任务正在处理中，请稍后再查询")
                        
                else:
                    st.error(f"❌ {error}")

elif tab_selection == "📥 下载结果":
    st.header("📥 下载批处理结果")
    
    # 输入Batch ID
    batch_id_input = st.text_input(
        "Batch ID",
        value=st.session_state.download_batch_id,
        help="输入要下载结果的批处理任务ID",
        key="download_batch_id_input"
    )
    st.session_state.download_batch_id = batch_id_input
    
    # 快速填入当前任务ID
    if st.session_state.batch_id and st.button("📋 使用当前任务ID", key="download_use_current"):
        st.session_state.download_batch_id = st.session_state.batch_id
        st.rerun()
    
    if st.button("📥 下载结果", type="primary"):
        if not api_key:
            st.error("请输入API Key")
        elif not batch_id_input:
            st.error("请输入Batch ID")
        else:
            with st.spinner("正在下载结果..."):
                content, error = download_batch_results_by_batch_id(api_key, batch_id_input)
                
                if content:
                    st.success("✅ 下载成功！")
                    
                    # 解析结果并转换为CSV
                    try:
                        lines = content.strip().split('\n')
                        results = []
                        
                        for line in lines:
                            if line.strip():
                                data = json.loads(line)
                                custom_id = data.get('custom_id', '')
                                
                                if data.get('response') and data['response'].get('body'):
                                    choices = data['response']['body'].get('choices', [])
                                    if choices:
                                        result_text = choices[0].get('message', {}).get('content', '')
                                        results.append({
                                            'ID': custom_id,
                                            'Result': result_text
                                        })
                        
                        if results:
                            # 创建DataFrame
                            df = pd.DataFrame(results)
                            
                            # 显示结果预览
                            st.subheader("📊 结果预览")
                            st.dataframe(df, use_container_width=True)
                            
                            # 提供下载按钮
                            csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                            st.download_button(
                                label="💾 下载CSV文件",
                                data=csv_data,
                                file_name=f"batch_results_{int(time.time())}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.warning("⚠️ 未找到有效的结果数据")
                            
                    except Exception as e:
                        st.error(f"❌ 解析结果失败: {str(e)}")
                        
                        # 显示原始内容
                        with st.expander("📄 查看原始内容"):
                            st.text(content)
                else:
                    st.error(f"❌ {error}")

# 页脚
st.markdown("""
---
<div style="text-align: center; color: #64748b; padding: 1rem;">
    <p>🤖 智谱AI Batch API 工具 | 使用Streamlit构建</p>
    <p>支持批量文本处理，提高API调用效率</p>
</div>

""", unsafe_allow_html=True)
