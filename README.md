# AI问答处理系统

这是一个基于讯飞星火大模型API的批量问答处理系统，可以读取问题文件并自动生成详细的回答。

## 功能特点

- 支持批量处理问题文件
- 自动生成包含问题、知识点、答案和拓展的markdown格式回答
- 支持断点续传，中断后可从上次处理位置继续
- 优雅的信号处理，支持Ctrl+C安全退出
- 实时显示处理进度
- 自动保存处理结果

## 系统要求

- Python 3.x
- websocket-client 库

## 安装依赖

```bash
pip install websocket-client
```

## 配置说明

在运行程序之前，请按照以下步骤配置环境：

1. 复制环境变量示例文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入您的星火大模型 API 凭证：
   ```ini
   SPARK_APP_ID=your_app_id_here
   SPARK_API_SECRET=your_api_secret_here
   SPARK_API_KEY=your_api_key_here
   SPARK_API_URL=your_api_url_here
   ```

注意：请勿将包含实际API凭证的 `.env` 文件提交到代码仓库中。

## 使用方法

1. 准备问题文件
   - 创建一个文本文件（默认为 `questions.txt`）
   - 每行写入一个问题
   - 空行会被自动跳过

2. 运行程序
   ```bash
   python main.py
   ```

3. 查看结果
   - 程序会生成一个markdown格式的答案文件（默认为 `answers.md`）
   - 每个问题的回答包含：问题、知识点、答案、拓展四个部分

## 处理流程

1. 读取问题文件，统计总问题数
2. 检查是否存在未完成的处理进度
3. 逐个处理问题：
   - 向星火API发送请求
   - 接收并处理回答
   - 保存为markdown格式
   - 实时显示进度
4. 支持随时中断，下次运行时从断点继续

## 文件说明

- `main.py`: 主程序文件
- `questions.txt`: 输入的问题文件
- `answers.md`: 生成的答案文件

## 错误处理

- 自动检查API凭证是否配置
- 检查输入文件是否存在
- 处理WebSocket连接错误
- 支持优雅退出

## 注意事项

1. 请确保正确配置星火API凭证
2. 问题文件需使用UTF-8编码
3. 建议定期备份生成的答案文件
4. 如需中断处理，请使用Ctrl+C，程序会自动保存进度

## 开发说明

### 核心类和方法

- `Ws_Param`: 处理WebSocket连接参数和URL生成
- `ask_spark()`: 向星火模型发送请求并获取答案
- `process_questions()`: 处理问题文件的主要逻辑
- `signal_handler()`: 处理中断信号

### 扩展开发

如需扩展功能，可以：

1. 修改问答格式：调整 `prompt` 变量
2. 更改模型参数：修改 `gen_params()` 中的参数
3. 自定义输出格式：修改 `markdown_output` 模板

## 许可证

MIT License