# 智谱AI Batch API 工具 - Streamlit版本

这是一个使用Streamlit构建的智谱AI批处理工具，提供与原始Express应用相同的功能。

## 功能特性

- 📤 **创建批处理任务**: 上传CSV文件，批量调用智谱AI API
- 🔍 **查询任务状态**: 实时监控批处理任务进度
- 📥 **下载结果**: 获取处理完成的结果文件
- ⚙️ **灵活配置**: 支持多种模型参数和提示词设置
- 🎨 **现代界面**: 美观的用户界面，响应式设计

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行应用

1. 确保后端Express服务器正在运行（端口3000）
2. 启动Streamlit应用：

```bash
streamlit run app.py
```

3. 在浏览器中访问 `http://localhost:8501`

## 使用说明

### 1. 配置设置
在侧边栏中配置：
- API Key（智谱AI的API密钥）
- 模型参数（模型类型、Token数、Temperature、Top P）
- 提示词（系统提示词和用户提示词）

### 2. 创建任务
- 上传包含待处理文本的CSV文件
- 系统会读取第一列数据进行处理
- 点击"创建批处理任务"按钮

### 3. 查询状态
- 输入Batch ID和API Key
- 查看任务进度和状态
- 支持自动刷新功能

### 4. 下载结果
- 任务完成后，输入Batch ID和API Key
- 下载包含处理结果的CSV文件
- 支持结果预览

## 注意事项

- 需要先启动后端Express服务器
- 确保API Key有效且有足够的配额
- CSV文件格式要求：第一列为待处理的文本内容
- 大文件处理可能需要较长时间，请耐心等待

## 技术栈

- **前端**: Streamlit
- **后端**: Express.js (复用现有API)
- **数据处理**: Pandas
- **HTTP请求**: Requests